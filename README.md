# BobTheBot

**An AI-controlled OSRS bot runtime — developed entirely by AI agents, never by hand.**

The goal: bootstrap a working OSRS bot without a human ever opening the game client manually. An agent does all of it through the MCP server: registration, login, gameplay automation, strategy changes.

Two things co-evolve:
- **The bot runtime** — backends, task engine, semi-agentic auth (visible browser + human OTP/CAPTCHA), test fixtures
- **The MCP server** — 30+ tools for agents to control the bot, take screenshots, fill forms, click buttons, detect page state

---

## Quick Start

### Install
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"                    # core + tests
# Optional: pip install -e ".[dev,cv]"    # + computer-vision backend
```

### Verify Everything Works
```bash
pytest -q                                  # 68 unit tests (all passing)
python -m radon cc bobthebot/ -s -a       # Code complexity: A-rated
python -m pyright bobthebot/               # Type checking: clean
bobthebot-run status                       # Check runtime state
```

### Using the MCP Server (For Claude Agents)
```bash
# Start the JSON-RPC stdio server
bobthebot-run mcp

# From another terminal, call a tool:
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n' | python -m bobthebot.mcp_server
printf '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"bob_auth_guide_step","arguments":{}}}\n' | python -m bobthebot.mcp_server
```

### CLI Commands (For Testing)
```bash
# Process/runtime status
bobthebot-run status
bobthebot-run runtime-status

# List backends, tasks, MCP tools
bobthebot-run backends
bobthebot-run tasks
bobthebot-run tools

# Start runtime (Xvfb + RuneLite)
bobthebot-run runtime-start
bobthebot-run runtime-stop

# Take a screenshot (ASCII art, refreshes every 1 second)
bobthebot-run see --live                   # Press Ctrl-C to exit

# Direct tool calls
bobthebot-run tool bob_auth_guide_step
bobthebot-run tool bob_auth_save_credentials --args '{"email":"you@example.com","password":"secret"}'
```

---

## Architecture

### Core Modules
| Module | Responsibility |
|--------|-----------------|
| `config.py` | Environment-driven config (browser path, display, Jagex URLs, logs dir) |
| `processes.py` | Process supervision (Xvfb, RuneLite, visible Chrome) |
| `browser.py` | Chrome DevTools Protocol client (navigate, eval, fill fields, click, take screenshots) |
| `auth.py` | Registration/login state machine + semi-agentic guide step (detects CAPTCHA, OTP, signals when human input needed) |
| `app.py` | Facade composing config, processes, auth, engine |
| `engine.py` | Threaded bot engine with lifecycle (start/stop/pause/resume) + task selection |
| `backends/` | Game client adapters (null, x11-cv, dreambot) |
| `mcp_server.py` | Hardened JSON-RPC 2.0 stdio dispatcher (validates messages, handles parse errors, rejects NaN/Infinity) |
| `mcp_tools.py` | Declarative tool registry + schemas |
| `tools/` | Tool groups (auth, runtime, tasks, input) |

### Semi-Agentic Auth Flow
The bot can automate most of registration/login, but **Cloudflare Turnstile blocks headless Chrome**. Solution: open a **visible Chrome window** so the user can:
- Solve the CAPTCHA manually
- Enter email verification codes
- Perform 2FA if needed

The `guide_step` tool returns:
- Current page state (e.g., `awaiting_captcha`, `awaiting_email_code`, `logged_in`)
- Screenshot of the current page
- List of visible buttons and inputs
- `needs_user` flag (true if waiting for human interaction)
- `suggested_action` (what to tell the user)

**Example flow**:
```
1. bot_auth_restart_browser url=https://account.jagex.com/en-GB/sign-up
2. bot_auth_register_start email=... password=... display_name=...
3. bot_auth_guide_step
   → returns: state="awaiting_captcha", needs_user=true, screenshot="path.png"
4. User solves CAPTCHA in the visible Chrome window
5. bot_auth_guide_step
   → returns: state="awaiting_email_code", needs_user=true
6. User enters the OTP, bot calls: bob_auth_continue email_code=123456
7. bot_auth_guide_step
   → returns: state="logged_in", needs_user=false
```

### MCP Tools (30+)

| Category | Count | Examples |
|----------|-------|----------|
| **Auth** (12) | Semi-agentic registration/login | `bob_auth_guide_step`, `bob_auth_wait`, `bob_auth_click_text`, `bob_auth_restart_browser`, `bob_auth_register_start`, `bob_auth_login_start`, `bob_auth_continue`, `bob_auth_screenshot` |
| **Runtime** (10) | Process + engine control | `bob_status`, `bob_runtime_start`, `bob_runtime_stop`, `bob_backend_list`, `bob_backend_set`, `bob_engine_start`, `bob_engine_stop`, `bob_engine_pause`, `bob_engine_resume` |
| **Tasks** (4) | Task selection + observation | `bob_task_list`, `bob_task_schema`, `bob_set_task`, `bob_observe` |
| **Observation** (4) | Game state snapshots | `bob_player`, `bob_inventory`, `bob_skills`, `bob_nearby` |
| **Raw Input** (4) | Direct mouse/keyboard | `bob_click`, `bob_type_text`, `bob_press_key`, `bob_interact` |

For the full list, run `bobthebot-run tools` or call `tools/list` on the MCP server.

---

## Backends

| Name | How It Works | Use Case | Status |
|------|-------------|----------|--------|
| `null` | Returns dummy responses | Testing MCP structure, validating tool schemas | ✅ Safe default |
| `x11-cv` | X11 screenshots + xdotool input | Headless RuneLite on Xvfb (requires `[cv]` deps) | ✅ Works |
| `dreambot` | HTTP bridge to Java DreamBot script | RuneLite with DreamBot script at localhost:19132 | ⚠️ Optional |

Select with `--backend NAME` or via `bob_backend_set` tool.

---

## Auth Configuration

### Saving Credentials
```bash
bobthebot-run tool bob_auth_save_credentials profile=default email=you@example.com password=secret
```

Stored (encrypted on disk, chmod 0600) at `~/.config/bobthebot/auth/credentials.json`.

### Email OTP Providers (Priority Order)
1. **Direct env var**: `export BOBTHEBOT_EMAIL_CODE=123456`
2. **Script**: `export BOBTHEBOT_EMAIL_CODE_COMMAND="my-script.sh"` (receives `BOBTHEBOT_PROFILE`, `BOBTHEBOT_EMAIL`, `BOBTHEBOT_PURPOSE`)
3. **IMAP**: `BOBTHEBOT_IMAP_HOST=imap.gmail.com BOBTHEBOT_IMAP_USER=... BOBTHEBOT_IMAP_PASSWORD=...`

### Registration / Login Example
```bash
# Save credentials once
bobthebot-run tool bob_auth_save_credentials profile=mybot email=user@example.com password=secret

# Start registration (opens visible Chrome)
bobthebot-run tool bob_auth_register_start profile=mybot

# Check state (take screenshot, detect CAPTCHA/OTP, get suggestions)
bobthebot-run tool bob_auth_guide_step

# If needs_user=true, user acts in Chrome window, then:
bobthebot-run tool bob_auth_guide_step  # check again

# If awaiting_email_code, submit it:
bobthebot-run tool bob_auth_continue profile=mybot email_code=123456

# Confirm logged in:
bobthebot-run tool bob_auth_guide_step
```

---

## Development

### Running Tests
```bash
pytest -q                                 # 68 unit tests (< 3 seconds)
pytest tests/test_auth.py -v             # Single test file
pytest tests/test_auth.py::test_guide_step -v  # Single test
```

All tests use fake stubs (FakeBrowser, FakeProcesses, FakeBackend) — no real browser, network, or game client needed.

### Code Quality
```bash
python -m radon cc bobthebot/ -s -a      # Cyclomatic complexity (target: A)
python -m radon mi bobthebot/ -s         # Maintainability index (target: A)
python -m pyright bobthebot/              # Type checking (target: clean)
```

### Development Rules
- **Logic is backend-agnostic**: Task code never directly uses CV, DreamBot, Java, or shell — use backend capabilities
- **MCP stays thin**: Tools adapt calls to `BotApp`, don't contain core logic
- **Tests are self-contained**: No RuneLite, Xvfb, DreamBot, or browser required
- **Credentials are plaintext but secure**: Stored with chmod 0600; never logged

---

## Memory System (For Agents)

For future agent sessions, comprehensive memory is available:

**Quick start** (read these first):
- `Agent Workflow Guide` — how to code on BobTheBot, common tasks, Serena usage
- `Consolidated Context (2026-05-16)` — full architecture + all tools
- `Local Environment Setup` — venv, directories, CLI commands
- `Architecture Deep Dive` — module responsibilities, data flow

**Reference**:
- `Lessons Learned & Pitfalls` — validated patterns, design anti-patterns
- `Troubleshooting Guide` — 20+ common issues + how to fix them

See `.claude/MEMORY.md` for the full index. Memories are persisted in Claude Code's harness and restored across sessions.

---

## Project Status

✅ **Completed (2026-05-16)**:
- Semi-agentic auth with visible browser (Cloudflare Turnstile compatible)
- 1-second terminal viewer (`--live` default)
- 30+ MCP tools with schemas
- Hardened JSON-RPC server (malformed JSON recovery, NaN/Infinity rejection)
- 68 unit tests (all passing)
- A-rated code complexity and maintainability
- Full API documentation and memory system

🟡 **Manual testing needed**:
- Live Jagex registration/login with real credentials
- State detection rules against live Jagex pages
- Edge cases (new security checks, page layout changes)

🔮 **Future priorities** (not started):
- Real OTP automation (Gmail/IMAP integration)
- Behavioral evasion (jitter, breaks, realistic typing)
- Multi-skill gameplay content
- Advanced CV-based task recognition

---

## Dependencies

| Tool | Purpose | Install |
|------|---------|---------|
| Python ≥ 3.11 | Runtime | Usually pre-installed |
| chafa | Terminal image rendering | `apt install chafa` |
| google-chrome | Auth browser automation | `apt install google-chrome-stable` |
| java | RuneLite (optional) | `apt install default-jre` |
| Xvfb | Virtual display (optional) | `apt install xvfb` |

Optional CV backend requires: OpenCV, scikit-image, Pillow, numpy.

---

## Example: Automated Login (For Agents)

```python
# This is what an agent would do:
from bobthebot.app import BotApp

app = BotApp()

# 1. Save credentials
app.auth_save_credentials("main", "user@example.com", "password123")

# 2. Start login (opens visible Chrome)
result = app.auth_login_start(profile="main")
print(f"Started login at {result['url']}")

# 3. Guide loop: take screenshots until logged in
max_attempts = 20
for i in range(max_attempts):
    guide = app.auth_guide_step("main")
    
    if guide["needs_user"]:
        print(f"Need user action: {guide['suggested_action']}")
        print(f"Screenshot: {guide['screenshot']}")
        # User solves CAPTCHA / enters OTP manually
        input("Press Enter when done in Chrome window...")
        continue
    
    if guide["state"] == "logged_in":
        print("Login successful!")
        break
    
    if guide["state"] == "awaiting_email_code":
        # If env var set, auto-submit; otherwise ask user
        result = app.auth_continue(profile="main")
        print(f"Submitted email code: {result}")
        continue
    
    print(f"State: {guide['state']}, Message: {guide['message']}")
    time.sleep(1)
```

---

## Help & Docs

- **Setup instructions**: See [Local Environment Setup](docs/) in memory
- **Troubleshooting**: See [Troubleshooting Guide](docs/) in memory
- **Lessons learned**: See [Lessons Learned & Pitfalls](docs/) in memory
- **Architecture**: See [Architecture Deep Dive](docs/) in memory
- **Isolated Bolt/RuneLite setup**: See [docs/isolated-bolt-runelite-demo.md](docs/isolated-bolt-runelite-demo.md)

---

## License

[LICENSE](LICENSE)

---

**Made by AI, for AI.** BobTheBot is designed to be controlled entirely by AI agents through MCP tools. No manual browser interaction, no hardcoded flows, just agent-driven automation.
