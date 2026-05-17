# Progress, smells, risks, next steps - 2026-05-14

## Progress made
- Rebuilt project foundation around installable `bobthebot` package.
- Added MCP-ish stdio server with tool validation and many bot/runtime/auth tools.
- Added typed runtime/domain models, backend registry, task registry, capability-aware task selection.
- Added DreamBot semantic backend for local Java bridge, CV/X11 backend, null backend.
- Added process supervisor for Xvfb/RuneLite/browser.
- Added CDP browser controller and auth service for registration/login.
- Added plaintext credential persistence, env-code verification provider, screenshot/status/continue flows.
- Added README docs and example CLI usage.
- Tests increased to 38 passing, all fake/no real browser/network required.

## Current working tree summary
- Modified tracked: `.gitignore`, `README.md`, `osbc/osbc_mcp_server.py`.
- New untracked intended: `pyproject.toml`, `bobthebot/`, `tests/`.
- Ignored runtime/local artifacts: `.venv/`, `.runtime/`, pycache, pytest cache.
- `osbc/RuneLite.jar` remains in repo as pre-existing file.

## Known risks / likely bugs
- Auth URLs/selectors may be stale. Jagex pages can change; current defaults are `https://account.jagex.com/en-GB/sign-up` and `/login`, but real pages may redirect or require additional fields.
- `BrowserController.navigate()` sleeps only 1 second after navigation; may need smarter wait: document ready state, network idle-ish, selector wait.
- `BrowserController.evaluate()` only returns `value`; if CDP returns unserializable objects or exception details, current code may hide useful errors.
- `AuthService._start_flow()` ignores whether fill/click actually succeeded; should report per-field success and fail if email/password fields were not found.
- `AuthService.continue_flow()` uses broad selectors for code, including any text input; could fill wrong field if page is unexpected.
- `AuthService.detect_state()` is text/URL heuristic only; needs real page observation after a live attempt.
- `CredentialStore` is intentionally plaintext per user request, but this is unsafe; password is redacted from outputs, not from file.
- `mcp_server.py` is hand-rolled MCP-ish JSON-RPC, not official SDK. Good enough for local stdio clients but may miss exact protocol details.
- `ProcessSupervisor.stop_all()` includes both `browser` and legacy `chromium`; OK, but statuses include both.
- `ProcessSupervisor.start_browser(headless=True)` uses `--headless=new`; if site behaves differently headless, may need visible/virtual display mode. Since Xvfb not installed locally, visible mode likely blocked unless user installs Xvfb or sets DISPLAY.
- `EnvVerificationProvider` only reads env vars; no Gmail/IMAP automation yet. Fully no-human registration will likely require email-code provider implementation.
- There is no actual CAPTCHA bypass by design. User prefers no human; if CAPTCHA appears, current system stops and reports state.
- `auth.py` imports `re` but does not currently use it; harmless cleanup candidate.

## Strong next implementation steps
1. Live dry-run auth open/status against Jagex account page using `bob_auth_open` or `bob_auth_register_start` with throwaway/test credentials only if user provides them. Capture snapshot/screenshot and adjust selectors/state detection.
2. Add `wait_for_selector`, `wait_for_text`, and document-ready wait to `BrowserController`.
3. Make `_start_flow()` return detailed field results: `email_filled`, `password_filled`, `display_name_filled`, `submit_clicked`.
4. Add Gmail connector verification provider using available Gmail plugin tools if user wants no-human email-code retrieval. Alternative: add IMAP provider configured by env vars.
5. Add tests for CDP event/response interleaving. Current implementation supports it, but no direct fake websocket unit test yet.
6. Consider moving MCP schema/tool definitions to declarative registry to reduce `mcp_server.py` size.
7. Add `bob_auth_set_visible_browser` or `headless` option to auth start/open tools if debugging headless issues.
8. Add runtime cleanup command specifically for browser: `bob_auth_browser_stop` or reuse `bob_stop_runtime`.

## Commands used for validation
- `.venv/bin/python -m pip install -e '.[dev]'`
- `.venv/bin/pytest -q` -> `38 passed`
- `python3 -m py_compile $(find bobthebot tests -name '*.py') osbc/osbc_mcp_server.py`
- `.venv/bin/bobthebot-run tool --name bob_auth_save_credentials ...` then `bob_auth_forget_credentials`
- `.venv/bin/bobthebot-run auth-status`

## Important user preferences
- User wants development fast and robust.
- User prefers no human involvement even for registration if possible.
- User explicitly accepts simple/plaintext credential persistence for speed and agent reuse.
- User expects AI agents to use the project through MCP/tools.