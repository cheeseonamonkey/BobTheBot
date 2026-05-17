# BobTheBot architecture snapshot - 2026-05-14

Project: `/home/alexander/Proj/BobTheBott`. Goal from README: AI-agent-centered OSRS automation with two co-evolving parts: bot runtime and MCP interface.

## Current repo state
- Old prototype remains under `osbc/` and `Scripts/MCPBridge.java`.
- New implementation is the `bobthebot/` package with pyproject metadata and tests.
- Legacy `osbc/osbc_mcp_server.py` is now only a compatibility entry point delegating to `bobthebot.mcp_server.main`.
- `.gitignore` ignores `.runtime/`, `.venv/`, egg-info, pytest cache, pycache, old OSBC runtime artifacts.

## Package modules
- `bobthebot/config.py`: `BotConfig`; env-driven config; runtime/log/config/auth dirs; RuneLite jar path; browser profile; Jagex URLs; browser debug port.
- `bobthebot/processes.py`: `ProcessSupervisor`; PID files; starts Xvfb, RuneLite, browser. Browser executable resolution order: `BOBTHEBOT_BROWSER`, `google-chrome`, `chromium`, `chromium-browser`. Browser runs with remote debugging and headless by default.
- `bobthebot/browser.py`: Chrome DevTools Protocol primitives. `CdpClient` correlates responses by id and buffers unrelated events. `BrowserController` discovers websocket URL, navigates, evaluates JS, fills/clicks first matching selector, snapshots page title/url/text, screenshots.
- `bobthebot/auth.py`: first-class registration/login subsystem. `CredentialStore` plaintext `.runtime/auth/credentials.json` chmod 0600. `AuthService` supports save/forget/status/register_start/login_start/continue/screenshot/open/verification_check. Detects states: missing_credentials, browser_unavailable, registration_page, login_page, awaiting_captcha, awaiting_email_code, awaiting_2fa, blocked, logged_in, unknown, error. CAPTCHA/security checks are surfaced, not bypassed.
- `bobthebot/models.py`: serializable dataclasses for `ActionResult`, `RuntimeStatus`, `EntityRef`, `Observation`, `PlayerState`, `InventoryItem`, `InventoryState`, `SkillState`, `SkillsState`; includes `safe_int` and `compact_dict`.
- `bobthebot/backends/base.py`: backend protocol and `NullBackend`.
- `bobthebot/backends/cv.py`: X11 screenshot/raw input backend using ImageMagick `import` and `xdotool`; semantic state methods return unavailable/empty states.
- `bobthebot/backends/dreambot.py`: semantic backend for local DreamBot Java bridge at `http://127.0.0.1:19132`; parses player/inventory/skills; supports nearby/interact/chat.
- `bobthebot/tasks.py`: task system with schema-backed `TaskRegistry`. Tasks: `idle`, `mining`. Mining requires `semantic_interact`, interacts with object target via `EntityRef`.
- `bobthebot/engine.py`: threaded `BotEngine`; start/stop/pause/resume, set_task with capability checks, status/observe/task schema.
- `bobthebot/registries.py`: `BackendRegistry` and specs for `null`, `x11-cv`, `dreambot`.
- `bobthebot/app.py`: `BotApp` composes config, backend registry, process supervisor, auth service, engine.
- `bobthebot/mcp_server.py`: hand-rolled MCP-ish JSON-RPC stdio server with `initialize`, `ping`, `tools/list`, `tools/call`, legacy aliases `list_tools`/`call_tool`. Validates tool args against schemas. Tool results are JSON text content and set `isError` based on payload.
- `bobthebot/cli.py`: `bobthebot-run` commands: `status`, `start`, `stop`, `backends`, `tasks`, `tool`, `auth-status`.

## MCP tools
Runtime/task tools: `bob_status`, `bob_backend_list`, `bob_backend_set`/`bob_set_backend`, `bob_runtime_status`, `bob_start_runtime`, `bob_stop_runtime`, `bob_observe`, `bob_player`, `bob_inventory`, `bob_skills`, `bob_nearby`, `bob_task_list`, `bob_task_schema`, `bob_engine_start`, `bob_engine_stop`, `bob_engine_pause`, `bob_engine_resume`, `bob_set_task`, `bob_task_set`, `bob_interact`, `bob_click`, `bob_type_text`, `bob_press_key`.

Auth tools: `bob_auth_save_credentials`, `bob_auth_forget_credentials`, `bob_auth_status`, `bob_auth_register_start`, `bob_auth_login_start`, `bob_auth_continue`, `bob_auth_screenshot`, `bob_auth_open`, `bob_auth_verification_check`.

## Validation status
Latest checked command: `.venv/bin/pytest -q` -> `38 passed in ~1.3s`. `python3 -m py_compile $(find bobthebot tests -name '*.py') osbc/osbc_mcp_server.py` also passes.

## Dependencies
Base dependency: `websockets>=12`. Dev extra: `pytest>=8`. CV extra: `mss`, `numpy`, `opencv-python`.