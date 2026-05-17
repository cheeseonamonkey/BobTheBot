---
name: troubleshooting_guide
description: How to diagnose and fix common issues in BobTheBot
metadata:
  type: project
---

# Troubleshooting Guide

## "Tests Failing"
**Symptom**: `pytest -q` shows red failures  
**Action**:
1. Run `pytest -q` to get summary
2. Run failing test with `-v` to see full output: `pytest tests/test_auth.py::test_name -v`
3. Check recent code changes — did you modify a function signature?
4. If test fixture (FakeBrowser, FakeProcesses), check the stub matches real implementation
5. Never skip tests; fix the underlying issue

**Common cause**: Function signature changed (e.g., added `headless` param) but test stub not updated.

## "State Detection Not Working"
**Symptom**: `bob_auth_guide_step` returns `state: "unknown"` but you expect a known state  
**Action**:
1. Check the screenshot: what text is actually on the page?
2. Look at `AUTH_STATE_RULES` in `auth.py` — are the keywords matching?
3. Run `bob_auth_guide_step` again to get screenshot path
4. Add new state rule if needed:
   ```python
   ("my_new_state", False, "New state detected.", ["new_check"], ("keyword1", "keyword2"))
   ```
5. Add hint in `_GUIDE_HINTS` dict
6. Re-test: `bob_auth_guide_step`

**Root cause**: Jagex page text changed; keywords are outdated.

## "Browser Not Starting"
**Symptom**: `bob_auth_restart_browser url=...` fails  
**Action**:
1. Check if `google-chrome` is installed: `which google-chrome`
2. If not found, set `BOBTHEBOT_BROWSER=/path/to/chrome`
3. Check `~/.config/bobthebot/` directory exists: `ls -la ~/.config/bobthebot/`
4. Check chrome process: `ps aux | grep chrome` (kill orphans if stuck: `killall -9 chrome`)
5. Try manual restart: `killall -9 chrome; sleep 1; bob_auth_restart_browser url=https://example.com`

**Root cause**: Chrome executable not found, or old process still running.

## "CAPTCHA/OTP Page Shows But Automation Stops"
**Symptom**: `bob_auth_guide_step` returns `needs_user=true` correctly, but user doesn't know what to do  
**Action**:
1. Check `suggested_action` in response — it should tell user what to do
2. If missing or wrong, update `_GUIDE_HINTS`:
   ```python
   "awaiting_captcha": (True, "Ask user to solve Cloudflare Turnstile in Chrome window, then call bob_auth_guide_step again"),
   ```
3. Make sure `needs_user=true` state is in hints dict
4. Restart: `bob_auth_guide_step` after user acts

**Root cause**: Hint missing or outdated for the state.

## "Credentials Not Saved"
**Symptom**: `bob_auth_save_credentials` succeeds but next call doesn't load them  
**Action**:
1. Check file exists: `cat ~/.config/bobthebot/auth/credentials.json | jq`
2. Check profile name matches: did you save as `"profile":"main"` but load as `"profile":"default"`?
3. Check format: must be valid JSON with `{"profile": {"email": "...", "password": "..."}}`
4. Re-save: `bob_auth_save_credentials profile=default email=... password=...`

**Root cause**: Profile name mismatch or corrupt JSON file.

## "Email OTP Code Not Found"
**Symptom**: `bob_auth_continue` fails because no code available  
**Action**:
1. Check env var first: `echo $BOBTHEBOT_EMAIL_CODE`
2. If blank, check command: `echo $BOBTHEBOT_EMAIL_CODE_COMMAND`
3. If command, test it manually:
   ```bash
   BOBTHEBOT_PROFILE=default BOBTHEBOT_EMAIL=user@example.com BOBTHEBOT_PURPOSE=auth sh -c "$BOBTHEBOT_EMAIL_CODE_COMMAND"
   ```
4. If that fails, set env var directly: `export BOBTHEBOT_EMAIL_CODE=123456`
5. Retry: `bob_auth_continue email_code=<code>`

**Root cause**: Command not executable, or env vars not set.

## "Multiple Chrome Windows Fighting"
**Symptom**: Clicks go to wrong window, screenshots black  
**Action**:
1. Kill all chrome: `killall -9 chrome`
2. Restart fresh: `bob_auth_restart_browser url=<url>`
3. Use `wait_for_websocket_url()` to ensure connection before next action
4. If on Xvfb/headless, may need to wait longer: check `BrowserController.wait_for_websocket_url(timeout=10.0)`

**Root cause**: Old chrome process still holding debugging port; new process can't connect.

## "Xvfb Not Found"
**Symptom**: `bob_start_runtime` fails because Xvfb missing  
**Action**:
1. Xvfb is optional if using browser on real DISPLAY
2. If you need virtual framebuffer: `apt-get install xvfb` (not available in this environment)
3. Workaround: use isolated Bolt/RuneLite setup on DISPLAY :98 (see `isolated-bolt-runelite-demo.md`)
4. Or use real RuneLite on system DISPLAY

**Root cause**: Virtual framebuffer not installed; not needed for browser-only testing.

## "Pyright Errors After Code Change"
**Symptom**: `python -m pyright bobthebot/` shows red squiggles  
**Action**:
1. Run full check: `python -m pyright bobthebot/`
2. Common issues:
   - Type mismatch: `str` vs `str | None` — add `| None` or check None before use
   - Undefined symbol: import missing — add `from .module import Symbol`
   - Return type mismatch — check function return annotation
3. Fix the error, re-run
4. Never use `# type: ignore` without explaining why in a comment

**Root cause**: Type annotation missing or wrong.

## "Radon Says Code is Too Complex"
**Symptom**: `python -m radon cc bobthebot/` shows files with D/E rating  
**Action**:
1. Find high-complexity functions: run with `-a` (all) flag
2. Break down the function into smaller helpers
3. Use table-driven approaches (like `AUTH_STATE_RULES`)
4. For `detect_state()`, refactor to loop over rules (already done; rating A)
5. Recheck: `python -m radon cc bobthebot/ -s -a`

**Root cause**: Long if-else chains, nested loops, high cyclomatic complexity.

## "Performance Issue: Slow State Detection"
**Symptom**: `bob_auth_guide_step` takes > 2 seconds  
**Action**:
1. Check browser connection: `BrowserController.wait_for_websocket_url(timeout=2.0)`
2. Profile the snapshot call: is evaluate() slow? Is navigate() not waiting?
3. Add sleep after navigation: `await asyncio.sleep(1.0)` (already in navigate())
4. For live pages, may need to wait for specific element: `await wait_for_selector(selector)`
5. Consider: is Jagex page JavaScript-heavy? May need longer wait.

**Root cause**: Browser not ready, network slow, page JavaScript rendering.

## "MCP Tool Response is Malformed"
**Symptom**: Tool call succeeds but client sees weird response (NaN, null, etc.)  
**Action**:
1. Check tool handler response: does it return JSON-serializable object?
2. Check for NaN/Infinity: `if math.isnan(x) or math.isinf(x)`
3. Test with `_tool_response()` wrapper — it normalizes bad payloads to errors
4. Check `_validate_number()` validation on schema level
5. Return clean dict: `{"ok": True, "result": ...}`

**Root cause**: Non-serializable object, NaN/Infinity value in response.

## Quick Diagnosis Checklist
```bash
# 1. Check tests
pytest -q

# 2. Check types
python -m pyright bobthebot/

# 3. Check complexity
python -m radon cc bobthebot/ -s -a

# 4. Check chrome
ps aux | grep chrome
which google-chrome

# 5. Check credentials
cat ~/.config/bobthebot/auth/credentials.json

# 6. Check env vars
echo $BOBTHEBOT_EMAIL_CODE
echo $BOBTHEBOT_BROWSER

# 7. Run specific test
pytest tests/test_auth.py::test_guide_step -v
```

## When All Else Fails
1. Clear state: `rm -rf ~/.config/bobthebot/ .runtime/`
2. Kill processes: `killall -9 python chrome java Xvfb`
3. Reinstall: `python -m pip install -e '.[dev]' --force-reinstall`
4. Run tests: `pytest -q`
5. Try again: `bob_auth_restart_browser url=https://example.com`