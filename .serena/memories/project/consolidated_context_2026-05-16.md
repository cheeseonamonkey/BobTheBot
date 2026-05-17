---
name: consolidated_context_2026-05-16
description: Full architecture snapshot, tool inventory, completed work, and near-term priorities
metadata:
  type: project
---

# BobTheBot: Consolidated Project Context — 2026-05-16

## Project Vision
**BobTheBot** is an AI-agent-centered OSRS (Old School RuneScape) bot runtime controlled exclusively via MCP tools.  
Goal: Bootstrap fully autonomous OSRS gameplay through Claude/Codex agents without human manual intervention on the game client.

Architecture: **dual co-evolution** of runtime implementation + agent-facing MCP interface.

## Recent Completion (2026-05-16)
✅ **Semi-agentic auth + 1s terminal viewer** — Full implementation committed (`8a86174`).
- Browser opens visible (non-headless) so users can interact with Cloudflare/OTP
- 4 new auth MCP tools added: guide_step, wait, click_text, restart_browser
- Terminal viewer refresh at 1s instead of 2s
- All 68 tests passing

## Current Architecture

### Package Structure
- **`bobthebot/`**: Main implementation (Python 3.11+)
  - `config.py`: Environment-driven runtime config
  - `processes.py`: Process supervision (Xvfb, RuneLite, visible browser)
  - `browser.py`: Chrome DevTools Protocol client (navigate, eval, form fill/click, DOM queries)
  - `auth.py`: Registration/login state machine + credential persistence + semi-agentic guide_step
  - `app.py`: Facade composing config, processes, auth, engine
  - `engine.py`: Threaded bot engine with lifecycle + task selection
  - `backends/`: Adapters (NullBackend, X11CvBackend, DreamBotBridgeBackend)
  - `tasks.py`: Task registry (idle, mining)
  - `mcp_server.py`: Hardened JSON-RPC stdio server (validates messages, handles parse errors, rejects NaN/Infinity)
  - `mcp_tools.py`: Declarative tool registration + schemas
  - `cli.py`: Entry points (bobthebot-run, bobthebot-mcp)
- **`tests/`**: 68 passing unit tests (all fake; no real browser/network/RuneLite required)
- **`pyproject.toml`**: Package metadata, console scripts, deps (websockets>=12)

### MCP Tool Surface
**30+ total tools** across 4 categories:

| Category | Count | Tools |
|---|---|---|
| Runtime/Task | 18 | status, backend_(list/set), runtime_(status/start/stop), observe, player, inventory, skills, nearby, task_(list/schema/set), engine_(start/stop/pause/resume) |
| Raw Input | 4 | click, type_text, press_key, interact |
| Auth | 12 | save_credentials, forget_credentials, status, register_start, login_start, continue, screenshot, open, verification_check, **guide_step**, **wait**, **click_text**, **restart_browser** |

### Semi-Agentic Auth Flow (NEW)
```
1. bob_auth_restart_browser url=<sign-up or login URL>    # opens visible Chrome
2. Bot or AI fills form fields automatically
3. bob_auth_guide_step                                     # take screenshot + detect state
   → returns {state, message, screenshot, visible_buttons, visible_inputs, needs_user, suggested_action}
4. If needs_user=true (CAPTCHA/OTP detected):
   - Tell user what to do in Chrome window
   - User solves CAPTCHA or enters OTP manually
5. bob_auth_guide_step                                     # check state again
6. If awaiting_email_code: bob_auth_continue email_code=<otp>
7. Confirm logged_in state
```

### Auth State Detection (Cloudflare-aware)
- `awaiting_cloudflare` — detects Turnstile challenge ("just a moment", "checking your browser")
- `awaiting_captcha` — CAPTCHA or security check
- `awaiting_email_code` — email verification required
- `awaiting_2fa` — two-factor code required
- `logged_in` — authentication complete
- `registration_page` / `login_page` — form pages (detected via URL)

### Email OTP Providers (Priority Order)
1. `BOBTHEBOT_EMAIL_CODE` environment variable
2. `BOBTHEBOT_EMAIL_CODE_COMMAND` — local script (receives profile, email, purpose)
3. IMAP via `BOBTHEBOT_IMAP_*` env vars

## Known Limitations & Next Steps

### High Priority
1. **Live Jagex page testing** — Real account + browser interaction needed to validate selectors and state detection against live Jagex pages
2. **Buffer initialization** — Xvfb/RuneLite buffer rendering delays; consider document-ready checks in BrowserController
3. **World switching** — If membership warnings appear, automated world switch logic needed

### Medium Priority
4. **Real email automation** — IMAP/Gmail integration for OTP retrieval (currently reads env/command only)
5. **State detection edge cases** — Jagex may add new UI elements; rules are table-driven for easy updates

### Technical Debt
6. **WebSocket CDP tests** — Add unit tests for CdpClient response ID matching, event buffering
7. **Tool registry split** — If `build_tools()` grows, split into runtime/task/input/auth groups (optional; A rating suggests low priority)

## Local Environment Facts
- ✅ `/usr/bin/google-chrome` (visible browser by default)
- ✅ `chafa` + ImageMagick `import` available
- ✅ `python3.11+` available
- ❌ `Xvfb` not found (but Bolt/RuneLite runbook uses isolated display :98)
- ✅ Isolated Bolt/RuneLite environment via custom wrapper (see `isolated-bolt-runelite-demo.md`)

## Code Quality
- Radon cyclomatic complexity: **A (1.90)**
- Radon maintainability index: **A** (all modules)
- Pyright diagnostics: **clean** for all production files
- MCP server hardened against: malformed JSON, missing methods, non-serializable payloads, NaN/Infinity

## Running the Project

### Setup
```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest  # → 68 passed
```

### MCP Testing
```bash
python -m bobthebot.mcp_server
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\\n' | python -m bobthebot.mcp_server
```

### CLI
```bash
bobthebot-run status
bobthebot-run tool bob_auth_guide_step
bobthebot-run auth-status
bobthebot-run see --live    # 1s terminal viewer (Ctrl-C to exit)
```

## User Preferences & Assumptions
- Fast, robust development prioritized over over-engineering
- No manual game client interaction; all via AI agents
- Plaintext credential storage acceptable for speed (chmod 0600)
- CAPTCHA/security checks surfaced to user, not bypassed
- Tool inputs validated at MCP boundary

## File Changes Since Last Handoff (2026-05-14 → 2026-05-16)
- ✅ Semi-agentic auth fully implemented
- ✅ Terminal viewer at 1s refresh
- ✅ All tests passing (68)
- ✅ Pyright clean
- ✅ Ready for live testing with real Jagex credentials