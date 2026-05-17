---
name: architecture_deep_dive
description: Detailed architecture: module responsibilities, data flow, and dependency graph
metadata:
  type: project
---

# BobTheBot Architecture Deep Dive

## Module Responsibility Map

### Core Entry Point: `bobthebot/app.py` (BotApp)
**Responsibility**: Facade composing all subsystems  
**Key methods**:
- `auth_*` — delegate to AuthService (8+ methods)
- `engine_*` — delegate to BotEngine (4 lifecycle methods)
- `observe`, `player`, `inventory`, `skills`, `nearby` — delegate to engine/backend
- `click`, `type_text`, `press_key`, `interact` — raw input delegation

**Pattern**: BotApp never implements logic; pure delegation. Tests don't mock BotApp; they mock its dependencies.

### Configuration: `bobthebot/config.py` (BotConfig)
**Responsibility**: Centralize all env-driven config  
**Key fields**:
- `browser_*` — Chrome executable, debug port, profile dir
- `jagex_*_url` — Register/login URLs
- `runelite_jar` — Path to RuneLite
- `display` — X11 display for Xvfb
- `logs_dir` — Where to write screenshots, logs
- `auth_credentials_file` — Plaintext credentials storage

**Pattern**: All env var reads in one place. No magic strings scattered in code.

### Process Supervision: `bobthebot/processes.py` (ProcessSupervisor)
**Responsibility**: Manage lifecycle of external processes (Xvfb, RuneLite, Chrome)  
**Key methods**:
- `start_xvfb()` — launches virtual framebuffer
- `start_runelite(memory_mb=512)` — starts game client with DISPLAY env
- `start_browser(url, headless=False)` — starts Chrome via command (visible by default now)
- `restart_browser(url, headless=False)` — kill + restart cleanly
- `stop_process(name)` — kill by name, cleanup PID file
- `is_running(name)` — check PID file still valid

**Pattern**: PID files track processes. Restart is "stop + start". Never assume process is alive; check PID.

### Browser Automation: `bobthebot/browser.py` (BrowserController)
**Responsibility**: Chrome DevTools Protocol client over WebSocket  
**Key methods**:
- `wait_for_websocket_url(timeout=10.0)` — poll /json endpoint until debugger available
- `navigate(url)` — navigate page, wait 1s, snapshot
- `page_snapshot()` — get {title, url, text}
- `evaluate(expression)` — run JS, return value
- `fill_first(selectors, text)` — try selectors in order, fill first match
- `click_first(selectors)` — try selectors in order, click first match
- `click_text(text)` — click element containing text (case-insensitive)
- `visible_buttons()` / `visible_inputs()` — DOM query helpers
- `screenshot(path)` — capture PNG to disk

**Pattern**: All browser ops are async. Selectors tried in order (first success wins). JS evaluation is the foundation; higher-level methods use evaluate().

### Authentication: `bobthebot/auth.py` (AuthService)
**Responsibility**: Registration/login state machine + semi-agentic flow  
**Key components**:
- `AUTH_STATE_RULES` — tuple of (state, ok, message, needs, keywords); table-driven detection
- `_GUIDE_HINTS` — map of state → (needs_user, suggested_action) for AI
- `CredentialStore` — plaintext email/password storage (chmod 0600)
- `AuthService` — orchestrates browser + state detection + credential mgmt

**Key methods**:
- `detect_state(snapshot)` → AuthResult — classify page (table-driven, O(n) rules)
- `guide_step(profile)` → dict — screenshot + state + buttons + inputs + hints + needs_user
- `wait_for_state(target_states, timeout)` → dict — poll until target state or timeout
- `register_start(email, password, display_name, submit=True)` — start registration flow
- `login_start(email, password, submit=True)` — start login flow
- `continue_flow(email_code, two_factor_code)` — submit OTP code
- `click_text(text)` → dict — click button by text
- `restart_browser(url)` → dict — kill + restart browser at URL

**Email OTP Providers** (checked in order):
1. `BOBTHEBOT_EMAIL_CODE` env var (direct)
2. `BOBTHEBOT_EMAIL_CODE_COMMAND` script (receives profile, email, purpose)
3. IMAP via `BOBTHEBOT_IMAP_*` env vars (if configured)

**Pattern**: State detection is deterministic (same snapshot → same state). Guide_step is the primary tool for semi-agentic flows; returns all info for Claude to decide next step.

### Bot Engine: `bobthebot/engine.py` (BotEngine)
**Responsibility**: Threaded game automation loop  
**Key components**:
- `backend` — selected BotBackend (null, x11-cv, dreambot, etc.)
- `task_registry` — semantic task definitions (mining, idle, etc.)
- `_engine_thread` — background thread running task loop

**Key methods**:
- `start()` / `stop()` / `pause()` / `resume()` — lifecycle
- `observe()` → dict — take backend screenshot
- `set_task(name, **kwargs)` — select task and config
- `status()` → dict — current state (running, task, stats)

**Pattern**: Engine is thread-safe. Task selection is capability-aware (can_mine?, can_fish? etc.). Each tick: observe → task.act() → sleep.

### Backend Adapters: `bobthebot/backends/` (BotBackend subclasses)
**Responsibility**: Decouple game client interaction from engine logic  

| Backend | How it works | Use case |
|---|---|---|
| `NullBackend` | Returns empty/dummy responses | Safe testing; MCP structure validation |
| `X11CvBackend` | X11 screenshots (ImageMagick) + xdotool input | Headless/Xvfb RuneLite |
| `DreamBotBridgeBackend` | HTTP bridge to Java script at :19132 | RuneLite + DreamBot script bridge |

**Interface**: All implement `BotBackend` with `{click, type_text, press_key, interact, observe, player, inventory, skills}`.

### MCP Server: `bobthebot/mcp_server.py` (BobMcpServer)
**Responsibility**: Harden JSON-RPC stdio protocol against malformed input  
**Key methods**:
- `handle(message)` → response | None — dispatch JSON-RPC request
- `serve()` — readline loop, handle per-line JSON, recover from parse errors
- `_tool_call_args(params)` → dict — normalize `params.arguments` (missing → {})
- `_tool_response(name, result)` → dict — serialize result, reject NaN/Infinity
- `_result()`, `_error()`, `_parse_error()` — response constructors

**Hardening**:
- Message must be object with `method` string
- `tools/call` must have `name` and optional `arguments` (normalized to {})
- Non-serializable/NaN payloads converted to tool-level errors
- Parse errors emit `-32700`, processing continues on next line
- Unknown tools return helpful "see tools/list" suggestion

**Pattern**: All tool responses go through `_tool_response()`. Server never crashes on bad tool output.

### MCP Tools: `bobthebot/tools/` (ToolGroup subclasses)
**Responsibility**: Declare tool schemas and route to app methods  

| File | Implements | Tools |
|---|---|---|
| `tools/auth.py` | AuthTools | 12 auth tools (guide_step, wait, click_text, restart_browser, etc.) |
| `tools/runtime.py` | RuntimeTools | status, backend_list, backend_set, runtime_start/stop |
| `tools/task.py` | TaskTools | task_list, task_schema, set_task |
| `tools/input.py` | InputTools | click, type_text, press_key, interact |

**Pattern**: Tool = (name, description, JSON schema, handler lambda). Handler receives args dict, returns JSON-serializable result. Schemas are declarative; shared `schema()` helper validates required fields.

### CLI: `bobthebot/cli.py`
**Responsibility**: Command-line entry points  

| Command | What it does |
|---|---|
| `bobthebot-run status` | Show process/engine status |
| `bobthebot-run tool <name>` | Call a tool by name |
| `bobthebot-run auth-status` | Check auth status for a profile |
| `bobthebot-run see [--live]` | Show current screen (1s refresh by default) |
| `bobthebot-run runtime-start` | Start Xvfb + RuneLite |
| `bobthebot-run mcp` | Start MCP server (JSON-RPC stdio) |

**Pattern**: All commands delegate to app or mcp_server. No business logic in CLI; thin wrapper.

## Data Flow: Registration Example

```
User calls: bob_auth_register_start(email=..., password=...)
  ↓
BotApp.auth_register_start() delegates to AuthService
  ↓
AuthService.register_start() 
  → calls processes.start_browser(headless=False)  [opens visible Chrome]
  → calls browser.navigate(register_url)            [navigates to Jagex]
  → fills email/password fields (fill_first)
  → clicks submit (click_first or click_text)
  → waits 1s
  → takes snapshot (page_snapshot)
  → calls detect_state(snapshot)
  → returns AuthResult with state, message, url, needs, data
  ↓
User calls: bob_auth_guide_step()
  ↓
AuthService.guide_step()
  → takes screenshot, gets page_snapshot()
  → detects state (is it "awaiting_captcha"? "awaiting_email_code"? "logged_in"?)
  → checks _GUIDE_HINTS for (needs_user, suggested_action)
  → returns {state, message, screenshot_path, visible_buttons, visible_inputs, needs_user, suggested_action}
  ↓
If needs_user=true:
  → Tell user: "Solve Cloudflare challenge in Chrome window"
  → User solves it in visible browser
  ↓
User calls: bob_auth_guide_step() again
  ↓
Repeat until state="logged_in"
```

## Dependency Graph

```
app.py (BotApp)
  ├── config.py (BotConfig)
  ├── processes.py (ProcessSupervisor)
  │   └── (spawns Xvfb, RuneLite, Chrome)
  ├── browser.py (BrowserController)
  │   └── (connects to Chrome DevTools via WebSocket)
  ├── auth.py (AuthService)
  │   ├── browser.py
  │   ├── processes.py
  │   └── auth_verification.py
  ├── engine.py (BotEngine)
  │   ├── backends/ (NullBackend, X11CvBackend, DreamBotBridgeBackend)
  │   └── tasks.py (TaskRegistry)
  └── mcp_server.py (BobMcpServer)
      ├── mcp_tools.py (ToolGroup registry)
      ├── tools/ (AuthTools, RuntimeTools, TaskTools, InputTools)
      └── app.py (delegates to BotApp methods)
```

## Testing Strategy

### Unit Tests (68 passing)
- FakeBrowser, FakeProcesses, FakeBackend stubs
- No real browser, network, or game client
- Fast (< 3s total)
- All features exercised (state detection, tool dispatch, error handling)

### Integration Tests (Manual)
- Real Jagex credentials + browser
- Real registration/login flow
- Real Turnstile CAPTCHA + OTP handling
- Not automated; requires user involvement

## Code Quality Invariants
1. **Tests**: Always green (pytest -q)
2. **Types**: Pyright clean (no ignores)
3. **Complexity**: Radon A (all files)
4. **Security**: Credentials plaintext but chmod 0600; never log password
5. **Error handling**: Validate at boundary, normalize tool responses
6. **Patterns**: Service/App/Tool layering; table-driven state detection; delegation