---
name: agent_workflow_guide
description: Quick start guide for AI agents working on BobTheBot; tool usage, testing patterns, and common tasks
metadata:
  type: project
---

# BobTheBot Agent Workflow Guide

## Quick Orientation (30 seconds)
**BobTheBot** = OSRS bot runtime controlled via 30+ MCP tools. Architecture: config → processes → browser/auth → engine.

Key files:
- `bobthebot/auth.py` — registration/login logic + semi-agentic guide_step
- `bobthebot/browser.py` — Chrome DevTools Protocol client
- `bobthebot/mcp_server.py` — hardened JSON-RPC/MCP dispatcher
- `bobthebot/tools/` — MCP tool definitions (auth, runtime, tasks, input)
- `tests/` — 68 unit tests (all fake; safe to run anytime)

## Development Environment
```bash
source "$HOME/venvs/whisper/bin/activate"
python -m pip install -e '.[dev]'
pytest -q  # → 68 passed
```

## Code Exploration with Serena
1. **Overview a file**: `mcp__serena__get_symbols_overview` with relative_path
2. **Find a symbol**: `mcp__serena__find_symbol` with name_path_pattern
3. **Read a symbol**: `mcp__serena__find_symbol` with include_body=True (not Read tool)
4. **Edit a symbol**: Use `mcp__serena__replace_symbol_body` or `mcp__serena__replace_content` (not Edit tool)
5. **Find usages**: `mcp__serena__find_referencing_symbols`

**Never use Read/Edit on code files — always use Serena.**

## Common Tasks

### Add a New Auth State Detection Rule
1. Open `bobthebot/auth.py` and locate `AUTH_STATE_RULES` tuple
2. Add new tuple: `(state_name, ok_bool, message, needs_list, term_keywords)`
3. Add hint in `_GUIDE_HINTS` dict
4. Test: `pytest tests/test_auth.py -k test_detect_state -v`

Example:
```python
("awaiting_new_check", False, "New security check detected.", ["security"], ("verify identity", "new check")),
```

### Add a New MCP Tool
1. Create tool handler in relevant service (e.g., `AuthService.my_method()`)
2. Add passthrough in `BotApp.auth_my_method()`
3. Add tool to `bobthebot/tools/auth.py`:
```python
Tool("bob_auth_my_tool",
     "Description for Claude",
     schema({...}, ["required_fields"]),
     lambda args: self.app.auth_my_method(...))
```
4. Test: `pytest tests/test_mcp_server.py -v`

### Test a Single Feature
```bash
pytest tests/test_auth.py -k test_guide_step -v
pytest tests/test_browser.py -k click_text -v
pytest tests/test_mcp_server.py -k malformed -v
```

### Check Code Quality
```bash
python -m radon cc bobthebot/ -s -a  # cyclomatic complexity
python -m radon mi bobthebot/ -s     # maintainability index
python -m pyright bobthebot/         # type checking
```

## MCP Server Behavior (Important!)
- Validates JSON-RPC messages (must be object with `method` string)
- Rejects non-serializable payloads, NaN, Infinity
- Continues processing on parse errors (sends `-32700`, keeps reading)
- Unknown tools return helpful error suggesting `tools/list`
- All tool responses normalized through `_tool_response()` helper

## Browser Automation Patterns
```python
# Fill form field
await browser.fill_first(['input[type="email"]'], email)

# Click by text (no selectors needed)
await browser.click_text("Create Account")

# Get visible buttons/inputs
buttons = await browser.visible_buttons()
inputs = await browser.visible_inputs()

# Take screenshot + analyze
snapshot = await browser.page_snapshot()
state = service.detect_state(snapshot)
```

## Auth Service Quick API
```python
# Start registration/login (opens visible Chrome)
result = auth.register_start(email=..., password=..., display_name=...)

# Check current state
result = auth.detect_state(snapshot)

# Guide step (screenshot + state + hints)
result = auth.guide_step()

# Wait for target state
result = auth.wait_for_state(["logged_in"], timeout=30.0)

# Click button by visible text
result = auth.click_text("Continue")
```

## Testing Patterns
```python
# Fake browser in unit tests
from tests.test_auth import FakeBrowser
browser = FakeBrowser(snapshot={...})

# Fake processes
from tests.test_auth import FakeProcesses
processes = FakeProcesses()

# Test auth state detection
snapshot = {"text": "too many attempts", "url": "..."}
result = auth.detect_state(snapshot)
assert result.state == "blocked"
```

## Debugging Tips
- **Browser stuck?** Use `bob_auth_restart_browser url=...` to kill+relaunch
- **State detection wrong?** Check `AUTH_STATE_RULES` against actual page text
- **Tool not found?** Run `bob_tools` or call `tools/list` via MCP
- **Tests fail?** Run `pytest -q` — should always be green; fix immediately
- **Selector wrong?** Use `bob_auth_guide_step` → check `visible_buttons`/`visible_inputs` to see what's actually on page

## Git Workflow
- Feature branches OK but keep them short (1-2 commits max)
- Commit messages: `feat:`, `fix:`, `docs:`, `test:` prefixes
- Push to main when tests pass and feature is complete
- No force-push to main

## When Context Gets Large
- Read MEMORY.md to reload latest context (auto-included in conversation)
- Key memories: consolidated_context_2026-05-16, implementation_complete_2026-05-16
- Use `/compact` when context window gets full; memories persist