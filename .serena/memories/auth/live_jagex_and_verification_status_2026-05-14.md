# Live Jagex auth and verification status - 2026-05-14

Current auth stack:
- `bobthebot.auth.AuthService` drives registration/login via Chrome DevTools Protocol through `BrowserController`.
- `BrowserController._devtools_endpoints()` now prefers `http://127.0.0.1:<port>/json` over `/json/version`; `/json/version` may return a browser-level websocket where `Page.enable` is unavailable. Test coverage exists in `tests/test_browser_controller.py`.
- `bob_auth_open` now returns raw snapshot fields plus `auth_state` from `AuthService.detect_state()`.
- `bob_auth_status` classifies current page state and reports `awaiting_captcha`, `awaiting_email_code`, `awaiting_2fa`, `blocked`, `logged_in`, `registration_page`, `login_page`, or `unknown`.
- CAPTCHA/security checks are detected and surfaced with `needs`, and registration/login snapshot paths are attached when states require intervention; no CAPTCHA bypass is implemented.

Email-code automation:
- Verification providers live in `bobthebot/auth_verification.py`.
- Provider order is env var -> command -> IMAP.
- Env vars: `BOBTHEBOT_EMAIL_CODE` or `BOBTHEBOT_EMAIL_CODE_<PROFILE>`.
- Command provider: `BOBTHEBOT_EMAIL_CODE_COMMAND`, receiving `BOBTHEBOT_PROFILE`, `BOBTHEBOT_EMAIL`, `BOBTHEBOT_PURPOSE`; stdout is scanned for a 6-8 digit code.
- IMAP provider env vars: `BOBTHEBOT_IMAP_HOST`, `BOBTHEBOT_IMAP_USER`, `BOBTHEBOT_IMAP_PASSWORD`, optional `BOBTHEBOT_IMAP_MAILBOX`.

Live result:
- Ran `.venv/bin/bobthebot-run tool --name bob_auth_open --args '{"url":"https://account.jagex.com/en-GB/sign-up"}'`.
- Chrome/CDP connection succeeded; previous `Page.enable wasn't found` bug is fixed.
- Jagex/Cloudflare returned title `Just a moment...` and text beginning `Are you a robot? Please complete the security check...`.
- Tool returned `auth_state.state == awaiting_captcha`, `needs == ["captcha"]`.
- Captured screenshot with `bob_auth_screenshot` at `.runtime/logs/auth-live-jagex.png`.

Code organization:
- `bobthebot/mcp_tools.py` now owns the declarative MCP tool registry (`Tool`, `schema`, `build_tools`).
- `bobthebot/mcp_server.py` now focuses on transport, dispatch, validation, and handlers.
- `auth.py` was split so verification-provider logic does not drag maintainability down.

Validation after changes:
- `.venv/bin/python -m compileall -q bobthebot tests` passed.
- `.venv/bin/pytest -q` => 44 passed.
- `.venv/bin/radon cc bobthebot -s -a` average complexity A (~1.96); notable remaining B methods are small dispatch/validation/browser/IMAP branches.
- `.venv/bin/radon mi bobthebot -s` => all modules A, including `auth.py` and `auth_verification.py`.

Remaining practical auth gap:
- Actual account registration cannot proceed unattended when Jagex/Cloudflare presents the security challenge. The system can open/report/capture the challenge and then continue after a human clears it in the browser session.