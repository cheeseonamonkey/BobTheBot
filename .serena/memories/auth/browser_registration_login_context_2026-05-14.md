# Auth/browser registration/login context - 2026-05-14

User requested fast development for registration/login, preferring no human involvement even for registration if possible. Chosen design: automate aggressively up to CAPTCHA/security/verification boundaries; do not bypass CAPTCHA/security checks. Plaintext credentials are acceptable per user preference.

## Local/system facts discovered
- `google-chrome` is installed at `/usr/bin/google-chrome`.
- `chromium`/`chromium-browser` were not found in PATH during discovery.
- `chafa` and ImageMagick `import` exist.
- `Xvfb` was not found in PATH during discovery. New browser path defaults to headless Chrome and does not require Xvfb.

## Official/account constraints researched
- Jagex account docs indicate Jagex accounts use email/password and default email-code 2FA; desktop access is through Jagex Launcher, with RuneLite support through Launcher.
- Useful docs:
  - Jagex Accounts FAQ: https://support.runescape.com/hc/en-gb/articles/34153372787857-Jagex-Accounts-FAQ
  - Upgrade character to Jagex account: https://support.runescape.com/hc/en-gb/articles/10682990186129-Upgrade-your-RuneScape-character-to-Jagex-account
  - Logging into Jagex Launcher: https://support.runescape.com/hc/en-gb/articles/34153405128593-Logging-into-the-Jagex-Launcher

## Auth implementation details
- New files: `bobthebot/browser.py`, `bobthebot/auth.py`, `tests/test_auth.py`.
- `BotConfig` auth/browser fields:
  - `browser_executable: str | None`
  - `browser_debug_port: int = 9222`
  - `jagex_register_url = https://account.jagex.com/en-GB/sign-up`
  - `jagex_login_url = https://account.jagex.com/en-GB/login`
  - `browser_profile = .runtime/config/browser-profile`
  - `auth_credentials_file = .runtime/auth/credentials.json`
- `ProcessSupervisor.start_browser(url=None, headless=True)` starts resolved browser with `--remote-debugging-port`, `--user-data-dir`, `--headless=new`, `--no-sandbox`, `--disable-dev-shm-usage`, `--no-first-run`, `--disable-first-run-ui`. PID file is `.runtime/browser.pid`.
- `BrowserController.websocket_url()` tries `/json/version` then `/json` and returns DevTools websocket URL.
- `CdpClient.send()` increments id, sends JSON, loops receiving frames until matching response id, storing unrelated frames in `events`.
- `BrowserController.fill_first()` and `click_first()` inject selector/text arrays via `json.dumps`, avoiding raw JS interpolation.
- `AuthService` methods exposed through MCP:
  - `save_credentials(profile,email,password)` stores plaintext and returns `{ok,profile,email,has_password}` with no password.
  - `forget_credentials(profile)` removes profile.
  - `status(profile)` snapshots page if DevTools available; otherwise returns `browser_unavailable` with has_credentials flag.
  - `register_start(profile,email?,password?,display_name?,submit=True)` saves provided credentials if present, starts browser at register URL, navigates, fills email/password/display name, optionally clicks submit, then classifies page state.
  - `login_start(...)` same pattern for login URL.
  - `continue_flow(profile,email_code?,two_factor_code?)` fills code from args or env verification provider and submits.
  - `screenshot(profile)` writes `.runtime/logs/auth-{profile}.png`.
  - `open(url)` starts browser/navigates to arbitrary URL.
  - `verification_check(profile,purpose)` checks configured provider.
- Verification provider currently implemented: `EnvVerificationProvider`; reads `BOBTHEBOT_EMAIL_CODE` or `BOBTHEBOT_EMAIL_CODE_{PROFILE}`. No Gmail/IMAP integration implemented yet.
- Selector constants: email selectors `input[type=email]`, `input[name=email]`, `#email`; password selectors `input[type=password]`, `input[name=password]`, `#password`; submit selectors `button[type=submit]`, `input[type=submit]`, `button[data-testid*=submit]`; display name selectors `input[name=displayName]`, `input[name=display_name]`, `#displayName`.
- State detection terms:
  - CAPTCHA/security: `captcha`, `verify you are human`, `security check` -> `awaiting_captcha` needs `[captcha]`.
  - Email code: `verification code`, `email code`, `check your email`, `enter the code` -> `awaiting_email_code`.
  - 2FA: `authenticator`, `two-factor`, `two factor`, `2fa` -> `awaiting_2fa`.
  - Blocked: `blocked`, `too many attempts`, `temporarily unavailable` -> `blocked`.
  - Authenticated-ish: `account created`, `welcome`, `logout`, `log out` -> `logged_in`.
  - URL contains `sign-up` or `create` -> `registration_page`; URL contains `login` -> `login_page`; else `unknown`.

## Example CLI usage
```bash
.venv/bin/bobthebot-run tool --name bob_auth_save_credentials --args '{"profile":"main","email":"you@example.com","password":"plaintext"}'
.venv/bin/bobthebot-run tool --name bob_auth_register_start --args '{"profile":"main","display_name":"Bob","submit":true}'
.venv/bin/bobthebot-run tool --name bob_auth_continue --args '{"profile":"main","email_code":"123456"}'
.venv/bin/bobthebot-run auth-status
```

## Smoke results
- `bob_auth_save_credentials` was smoke-tested with profile `smoke`; output redacted password; then `bob_auth_forget_credentials` removed it.
- `bobthebot-run auth-status` without a running DevTools browser returns `{ok:false,state:"browser_unavailable",message:"Browser DevTools websocket is not available"}`.
- Smoke-created `.runtime/auth/credentials.json` was removed after testing.