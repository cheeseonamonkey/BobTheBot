---
name: lessons_learned
description: Pitfalls, lessons, and validated approaches from BobTheBot development
metadata:
  type: feedback
---

# Lessons Learned & Pitfalls

## ✅ What Works Well

### Semi-Agentic Auth (Validated)
**Rule**: Visible browser + human interaction for Cloudflare/OTP steps works great.  
**Why**: Turnstile CAPTCHA blocks headless Chrome. Visible window + `needs_user` flag lets Claude tell user what to do, user acts, bot resumes. Clean separation.  
**How to apply**: When adding new security checks (2FA, new CAPTCHA types), extend `AUTH_STATE_RULES` + `_GUIDE_HINTS`. Keep `needs_user` flag clear.

### Table-Driven State Detection (Validated)
**Rule**: Use `AUTH_STATE_RULES` tuple + `detect_state()` instead of nested if-else chains.  
**Why**: Easy to add new states, easy to tweak keywords. Radon complexity stays A-rated.  
**How to apply**: New auth state? Add tuple to `AUTH_STATE_RULES`. No need to refactor detect_state().

### MCP Server Robustness (Validated)
**Rule**: Validate at the boundary (JSON-RPC + tool args), don't trust internal code.  
**Why**: Non-serializable/NaN payloads used to crash the server. Now normalized at tool-response layer.  
**How to apply**: New tool? Make sure `_tool_response()` can handle any payload. Reject NaN in schemas via `_validate_number()`.

### Hardened Tests (Validated)
**Rule**: Test fixtures must match real behavior exactly (FakeBrowser, FakeProcesses stubs).  
**Why**: Tests caught missing `headless` parameter in FakeProcesses.start_browser().  
**How to apply**: After signature change, update ALL fakes immediately. Run tests before committing.

## ⚠️ Pitfalls to Avoid

### Headless Chrome + Turnstile
**Problem**: Cloudflare Turnstile blocks headless Chrome. Started with headless=True default.  
**Lesson**: Visible browser is the only reliable path. Changed default to headless=False.  
**How to avoid**: If testing with Jagex/Turnstile, always use headless=False.

### Selector Drift
**Problem**: CSS selectors (email input, submit button) may change between Jagex page updates.  
**Lesson**: Store selectors in constants (`EMAIL_SELECTORS`, `PASSWORD_SELECTORS`) for easy updates.  
**How to avoid**: Use `visible_buttons()`/`visible_inputs()` in `guide_step` so Claude can see what's actually there. Add fallback text-based click (`click_text`).

### Process Proliferation
**Problem**: Multiple Java/RuneLite instances spawned; focus theft; screen capture confusion.  
**Lesson**: `ProcessSupervisor.restart_browser()` stops old PID before launching new one. Essential for clean state.  
**How to avoid**: Always call `restart_browser()` before critical operations, not just `start_browser()`.

### Buffer Rendering Delays
**Problem**: Xvfb/headless Chrome sometimes returns black frames on rapid snapshots.  
**Lesson**: Add small sleep after navigation (`await asyncio.sleep(1.0)` in navigate()). May need document-ready check.  
**How to avoid**: After navigation, add polling or wait-for-selector logic if state detection fails.

### Credentials in Logs
**Problem**: Plaintext credentials stored at `~/.config/bobthebot/auth/credentials.json` with chmod 0600.  
**Lesson**: User accepts this for speed. Never log the full credential dict; redact password in output.  
**How to avoid**: Always mask password in tool responses: `"has_password": True` instead of `"password": "..."`.

## 🔍 Testing Philosophy

### Tests Must Be Fast & Safe
**Rule**: All tests are unit tests with fakes (no real browser/network/RuneLite).  
**Why**: Fast (< 1s), safe to run anytime, no side effects.  
**How to apply**: New feature? Add unit test with fakes first. Live testing is manual (requires credentials/browser).

### Integration Testing is Manual
**Rule**: Auth flows need manual testing with real Jagex credentials (once we have them).  
**Why**: Jagex page selectors change; state detection rules need real-world validation.  
**How to apply**: Keep integration test checklist in docs: "Fill email", "Click continue", "See OTP prompt", etc.

## 🎯 Design Patterns

### The Service/App/Tool Layering
**Pattern**: Service (auth.py) → App passthrough (app.py) → MCP tool (tools/auth.py)  
**Why**: Decouples business logic from MCP protocol. Easy to test service in isolation.  
**How to apply**: New feature? Add to service, add passthrough in app, expose via tool.

### DOM Introspection Without Selectors
**Pattern**: `visible_buttons()` + `click_text()` + `visible_inputs()` let Claude see + interact without CSS knowledge.  
**Why**: Jagex page changes; selectors break. Button text is more stable.  
**How to apply**: When state detection fails, use `guide_step` to show Claude the actual DOM. Let Claude decide next action.

### _GUIDE_HINTS for Semi-Agentic Flows
**Pattern**: Each state → (needs_user: bool, suggested_action: str)  
**Why**: Claude knows when to pause and ask user, what to tell user, when to resume.  
**How to apply**: New blocker state? Add to `_GUIDE_HINTS` and set `needs_user=True` if human interaction needed.

## 📋 Future Work Priorities

### Next (High)
1. Live Jagex testing — validate selectors against real pages
2. Document exact registration/login flow with real screenshots
3. Add world-switch automation if membership warnings appear

### Later (Medium)
4. Gmail OTP integration (if user has Gmail plugin)
5. Robust document-ready checks in BrowserController
6. Task-level behavior metrics (click count, wait time, etc.)

## Code Quality Invariants
- **Tests**: Always green (pytest -q)
- **Types**: Pyright clean (no ignores)
- **Complexity**: Radon A for all files
- **Credentials**: Plaintext OK (chmod 0600), never log password
- **Errors**: Validate at boundary, normalize tool responses, never crash server