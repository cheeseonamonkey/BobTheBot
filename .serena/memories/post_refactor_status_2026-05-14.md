# Post-refactor status - 2026-05-14

## Current implementation state
- New installable Python package exists under `bobthebot/`.
- Existing legacy `osbc/osbc_mcp_server.py` is now a compatibility shim delegating to `bobthebot.mcp_server.main`.
- `pyproject.toml` exists with package metadata, console scripts, base dependency `websockets>=12`, optional `cv` deps, and dev deps `pytest>=8`, `radon>=6`.
- README documents architecture, MCP tools, auth automation, CLI examples, and development rules.

## Major subsystems
- `config.py`: env-backed `BotConfig`; runtime/log/config/auth dirs; browser executable/debug port; Jagex URLs; RuneLite jar path.
- `processes.py`: `ProcessSupervisor` manages Xvfb, RuneLite, browser PIDs. Browser resolution: `BOBTHEBOT_BROWSER`, `google-chrome`, `chromium`, `chromium-browser`. Browser starts headless by default with CDP port.
- `browser.py`: CDP client/controller. Response ID matching, event buffering, websocket URL discovery, navigation, evaluate, fill/click first selector, snapshot, screenshot.
- `auth.py`: auth state machine and credential store. Plaintext `.runtime/auth/credentials.json` chmod 0600. Auth tools support save/forget/status/register/login/continue/screenshot/open/verification-check. Current verification provider only reads `BOBTHEBOT_EMAIL_CODE` or `BOBTHEBOT_EMAIL_CODE_{PROFILE}`.
- `models.py`: serializable dataclasses plus shared JSON schema validation helpers. Shared validators are now used by MCP tool validation and task config validation.
- `backends/`: `NullBackend`, `X11CvBackend`, `DreamBotBridgeBackend`.
- `tasks.py`: schema-backed `TaskRegistry` with `idle` and `mining`; mining requires `semantic_interact`.
- `engine.py`: threaded lifecycle with pause/resume, capability-checked task selection.
- `mcp_server.py`: hand-rolled MCP-ish JSON-RPC server. Supports `initialize`, `ping`, `tools/list`, `tools/call`, plus legacy `list_tools`/`call_tool`. Validates args before tool handlers.
- `cli.py`: `bobthebot-run` commands: `status`, `start`, `stop`, `backends`, `tasks`, `tool`, `auth-status`.

## Current MCP tool surface
Runtime/task: `bob_status`, `bob_backend_list`, `bob_backend_set`/`bob_set_backend`, `bob_runtime_status`, `bob_start_runtime`, `bob_stop_runtime`, `bob_observe`, `bob_player`, `bob_inventory`, `bob_skills`, `bob_nearby`, `bob_task_list`, `bob_task_schema`, `bob_engine_start`, `bob_engine_stop`, `bob_engine_pause`, `bob_engine_resume`, `bob_set_task`, `bob_task_set`, `bob_interact`, `bob_click`, `bob_type_text`, `bob_press_key`.

Auth: `bob_auth_save_credentials`, `bob_auth_forget_credentials`, `bob_auth_status`, `bob_auth_register_start`, `bob_auth_login_start`, `bob_auth_continue`, `bob_auth_screenshot`, `bob_auth_open`, `bob_auth_verification_check`.

## Validation status
Last validation:
- `.venv/bin/pytest -q` -> `38 passed`
- `python3 -m py_compile $(find bobthebot tests -name '*.py') osbc/osbc_mcp_server.py` -> passed
- `.venv/bin/python -m radon cc bobthebot -s -a` -> package average complexity `A (1.90)`
- `.venv/bin/python -m radon mi bobthebot -s` -> all package modules maintainability `A`

## Refactor wins already done
- Removed duplicate JSON schema validation from MCP/task config by centralizing in `models.py`.
- Removed worst C-level radon hotspots: `BobMcpServer._validate_value` C(20) and task `_validate_task_value` C(16) no longer exist.
- `AuthService.detect_state()` is now table-driven via `AUTH_STATE_RULES`; URL detection split into `_detect_url_state`.
- `ProcessSupervisor.stop_all()` delegates to `stop_process()`.
- CLI split into `main`, `run_command`, `call_tool`.
- Browser websocket discovery avoids repeated `_websocket_from_page` calls.
- Added `radon>=6` to dev extra.

## Current working tree summary
- Modified tracked files: `.gitignore`, `README.md`, `osbc/osbc_mcp_server.py`.
- New untracked intended files/directories: `pyproject.toml`, `bobthebot/`, `tests/`.
- No leftover `.runtime` credential files or pycache artifacts at last check.
- `.venv/` exists locally and is ignored.

## Important behavior/policy context
- User wants fast, robust development and expects AI agents to operate the project through MCP/tools.
- User prefers no-human registration if possible, and explicitly allowed simple/plaintext credential persistence.
- CAPTCHA/security challenge bypass is intentionally not implemented; code detects/report states instead.
- Registration/login has not been live-tested against real Jagex pages yet. Selector/state tuning likely needed after a live page attempt.

## Remaining gaps / next best steps
1. Live auth page tuning: use `bob_auth_open` or `bob_auth_register_start` with test credentials to inspect actual Jagex page DOM/text/state and update selectors/waits.
2. Add smarter browser waits: document ready, selector wait, and maybe retry-after-navigation. Current `navigate()` sleeps 1 second.
3. Make auth start return field-level results: `email_filled`, `password_filled`, `display_name_filled`, `submit_clicked`. Current code ignores fill/click boolean results.
4. Add real email-code automation: Gmail connector provider if using connected Gmail plugin, or IMAP/env-command provider. Current provider only reads env vars.
5. Add direct fake-websocket tests for `CdpClient.send()` response-id matching and event buffering.
6. Split `mcp_server.py` into declarative tool registry modules. It is maintainable A now, but still large and will grow.
7. Consider official MCP SDK adoption later if exact protocol compatibility becomes important.
8. Consider visible browser mode/debug option. Current browser starts headless; local Xvfb was not found, but `google-chrome` is installed.

## Useful smoke commands
```bash
.venv/bin/bobthebot-run tasks
.venv/bin/bobthebot-run backends
.venv/bin/bobthebot-run auth-status
.venv/bin/bobthebot-run tool --name bob_auth_save_credentials --args '{"profile":"main","email":"you@example.com","password":"plaintext"}'
.venv/bin/bobthebot-run tool --name bob_auth_register_start --args '{"profile":"main","display_name":"Bob","submit":true}'
.venv/bin/bobthebot-run tool --name bob_auth_continue --args '{"profile":"main","email_code":"123456"}'
.venv/bin/bobthebot-run tool --name bob_auth_forget_credentials --args '{"profile":"main"}'
```

## Known local facts
- `google-chrome` exists at `/usr/bin/google-chrome`.
- `chromium` was not found during earlier discovery.
- `Xvfb` was not found during earlier discovery.
- `chafa` and ImageMagick `import` exist.