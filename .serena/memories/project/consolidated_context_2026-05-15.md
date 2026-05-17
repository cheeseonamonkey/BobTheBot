# BobTheBot: Consolidated Project Context - 2026-05-15

## Project Vision
**BobTheBot** is an AI-agent-centered OSRS (Old School RuneScape) bot implementation.  
Goal: Bootstrap a fully autonomous OSRS bot controlled exclusively by AI agents (Claude, Codex, etc.) through MCP tools—no human manual intervention on the game client.

Core architecture: **dual co-evolution** of runtime implementation + agent-facing MCP interface, each informing the other.

## Current Architecture

### Package Structure
- **`bobthebot/`**: New main implementation (Python 3.11+)
  - `config.py`: Environment-driven runtime config (dirs, browser, Jagex URLs, RuneLite jar path)
  - `processes.py`: Process supervision (Xvfb, RuneLite, browser) + browser executable resolution
  - `browser.py`: Chrome DevTools Protocol client for navigation, eval, form fill/click, snapshots
  - `auth.py`: Registration/login state machine + credential persistence (plaintext `.runtime/auth/credentials.json` chmod 0600)
  - `models.py`: Serializable dataclasses + shared JSON schema validation
  - `backends/`: Interchangeable runtime adapters (`NullBackend`, `X11CvBackend`, `DreamBotBridgeBackend`)
  - `tasks.py`: Schema-backed task registry (`idle`, `mining` with semantic interaction)
  - `engine.py`: Threaded bot engine with lifecycle (start/stop/pause/resume) and capability-aware task selection
  - `mcp_server.py`: Hand-rolled JSON-RPC stdio server (hardened against malformed messages, non-serializable payloads, NaN/Infinity)
  - `mcp_tools.py`: Declarative tool registration + schemas
  - `cli.py`: CLI entry points (`bobthebot-run`, `bobthebot-mcp`)
  - `app.py`: Composes config, backends, process supervisor, auth service, engine
- **`osbc/`**: Legacy prototype reference; `osbc_mcp_server.py` is now a compatibility shim to `bobthebot.mcp_server`
- **`tests/`**: 38 passing tests (all fake; no real browser/network/RuneLite required)
- **`pyproject.toml`**: Package metadata, console scripts, deps (`websockets>=12`), optional CV deps, dev deps (`pytest>=8`, `radon>=6`)

### MCP Tool Surface
**30 total tools** across 3 categories:

1. **Runtime/Task** (18): `bob_status`, `bob_backend_list`, `bob_backend_set`, `bob_runtime_status`, `bob_start_runtime`, `bob_stop_runtime`, `bob_observe`, `bob_player`, `bob_inventory`, `bob_skills`, `bob_nearby`, `bob_task_list`, `bob_task_schema`, `bob_engine_start`, `bob_engine_stop`, `bob_engine_pause`, `bob_engine_resume`, `bob_set_task`

2. **Raw Input** (4): `bob_interact`, `bob_click`, `bob_type_text`, `bob_press_key`

3. **Auth** (8): `bob_auth_save_credentials`, `bob_auth_forget_credentials`, `bob_auth_status`, `bob_auth_register_start`, `bob_auth_login_start`, `bob_auth_continue`, `bob_auth_screenshot`, `bob_auth_open`, `bob_auth_verification_check`

### Backend Strategies
- **`null`**: Safe default for testing MCP/engine without game client
- **`x11-cv`**: X11 screenshots (ImageMagick) + raw input (xdotool); semantic state returns unavailable/empty
- **`dreambot`**: HTTP bridge to local Java script (`Scripts/MCPBridge.java` at `:19132`); parses player/inventory/skills

### Auth Flow
1. Save credentials: `bob_auth_save_credentials`
2. Start registration/login: `bob_auth_register_start` or `bob_auth_login_start` (opens browser)
3. Fill email/password/display_name + submit automatically
4. If CAPTCHA/security check: `bob_auth_screenshot` to inspect, `bob_auth_continue` with manual state
5. If email code needed: `bob_auth_continue` (auto-reads `BOBTHEBOT_EMAIL_CODE` env var or command result)
6. Completion: `bob_auth_verification_check` to confirm logged in

Email-code providers (checked in order):
- `BOBTHEBOT_EMAIL_CODE` or `BOBTHEBOT_EMAIL_CODE_{PROFILE}` (direct env var)
- `BOBTHEBOT_EMAIL_CODE_COMMAND` (local script; receives `BOBTHEBOT_PROFILE`, `BOBTHEBOT_EMAIL`, `BOBTHEBOT_PURPOSE`)
- IMAP via `BOBTHEBOT_IMAP_HOST`, `BOBTHEBOT_IMAP_USER`, `BOBTHEBOT_IMAP_PASSWORD`, optional `BOBTHEBOT_IMAP_MAILBOX`

## Recent Hardening & Validation (2026-05-14)

### MCP Server Robustness
- ✅ JSON-RPC message validation: requires object, requires `method` string
- ✅ Malformed JSON parse-error recovery (`-32700`, continue processing)
- ✅ `tools/call` param/argument validation + bad shape detection
- ✅ Tool response serialization with `allow_nan=False`; non-serializable/NaN payloads → tool-level errors, not server crash
- ✅ Unknown tool detection with helpful error
- ✅ Shared non-finite number validation (`_validate_number`) rejects NaN/Infinity
- ✅ 38 passing pytest tests + regression coverage for above scenarios
- ✅ Pyright diagnostics clean for production files + test files

### Code Quality
- Radon cyclomatic complexity: **A (1.90)**
- Radon maintainability index: **A** (all modules)
- Worst hotspot removed: `AuthService.detect_state()` refactored to table-driven `AUTH_STATE_RULES`

## Known Gaps & Next Steps

### High Priority
1. **Live auth page tuning**: Jagex account page selectors/state detection not yet live-tested. Try `bob_auth_register_start` with test credentials; inspect DOM/text; adjust selectors if needed.
2. **Smarter browser waits**: `BrowserController.navigate()` currently sleeps 1s only. Need document-ready check, selector wait, possible retry-after-nav.
3. **Field-level auth results**: `AuthService._start_flow()` should return `{email_filled: bool, password_filled: bool, display_name_filled: bool, submit_clicked: bool}` instead of ignoring fill/click success.

### Medium Priority
4. **Real email-code automation**: Current provider only reads env vars. Add Gmail connector (if user has Gmail plugin) or IMAP/command automation.
5. **Fake websocket CDP tests**: Add unit tests for `CdpClient.send()` response ID matching and event buffering.
6. **Tool registry refactor**: Split `mcp_server.py` `build_tools()` into `_runtime_tools()`, `_task_tools()`, `_input_tools()`, `_auth_tools()` (optional; A rating suggests low priority).

### Local Environment Facts
- ✅ `google-chrome` at `/usr/bin/google-chrome`
- ✅ `chafa` and ImageMagick `import` available
- ✅ `python3.11+` available
- ❌ `Xvfb` not found
- ❌ `chromium` not found (fallback unused)

## Running the Project

**Install & test:**
```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest  # -> 38 passed
```

**Smoke MCP::**
```bash
python -m bobthebot.mcp_server
printf '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\",\"params\":{}}\\n' | python -m bobthebot.mcp_server
printf '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"bob_status\",\"arguments\":{}}}\\n' | python -m bobthebot.mcp_server
```

**CLI:**
```bash
bobthebot-run status
bobthebot-run backends
bobthebot-run tasks
bobthebot-run tool --name bob_task_schema --args '{"task":"mining"}'
bobthebot-run auth-status
bobthebot-run tool --name bob_auth_save_credentials --args '{"profile":"main","email":"you@example.com","password":"plaintext"}'
```

## User Preferences & Assumptions
- Fast, robust development preferred
- No manual browser/game interaction; all via AI agents & tools
- Plaintext credential persistence acceptable for speed/agent-reuse (password still redacted in outputs)
- CAPTCHA/security checks surfaced, not bypassed
- Tool inputs validated at MCP boundary (no bad state passed to runtime)

## Working Tree Status (2026-05-15)
- Modified tracked: `.gitignore`, `README.md`, `osbc/osbc_mcp_server.py`
- New untracked: `pyproject.toml`, `bobthebot/`, `tests/`
- Clean: no `.runtime` artifacts or pycache in git
- Last validation: pytest 38 passed, pyright clean, radon A/A

## Research Findings (2026-05-15)
- **Account Auth Reality**: Jagex OAuth2/Launcher makes direct automation hard (Java client EOL Jan 2026). Most successful bots use pre-created accounts. Auto-registration is secondary priority.
- **Bot Detection**: Behavioral analysis + hijacking detection (2025). Evasion requires Gaussian jitter, realistic breaks, YOLO CV for task recognition, ML adaptive models.
- **Similar Projects**: osrs-all (most advanced), RuneLite integration standard, node-based tasks, anti-detection layers essential.
- **Roadmap Priority**: Anti-detection → Task framework → CV integration → Multi-skill content. Skip direct Jagex automation for now; assume pre-created accounts.