# Project Context

Dense context for humans and future agents. Keep this page aligned with code when entrypoints, tools, or runtime assumptions change.

For the shortest operational checklist, read [agent-ops.md](agent-ops.md) first.

## Broad Intent

BobTheBot is an AI-agent-controlled Old School RuneScape automation runtime. The useful product is not just a bot loop; it is a local MCP/CLI surface that lets agents start the runtime, inspect screenshots/state, handle semi-manual authentication, and send raw or semantic game actions.

Current practical direction: use RuneLite through Bolt/Jagex Launcher compatibility on an isolated X display, drive it through the `x11-cv` backend, and keep DreamBot as legacy/experimental bridge code unless a Python backend is reintroduced.

## Current Entry Points

Install into the local venv before running commands:

```bash
cd /home/alexander/Proj/BobTheBot
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Main commands:

```bash
.venv/bin/bobthebot-run check
.venv/bin/bobthebot-run status
.venv/bin/bobthebot-run backends
.venv/bin/bobthebot-run tools
.venv/bin/bobthebot-run see --live
.venv/bin/bobthebot-mcp
```

Equivalent module forms:

```bash
.venv/bin/python -m bobthebot.cli tools --renderer none
.venv/bin/python -m bobthebot.mcp_server
```

Do not rely on system `python3` unless dependencies have been installed there. During the 2026-05-17 verification pass, system `python3 -m bobthebot.cli ...` failed with `ModuleNotFoundError: No module named 'websockets'`; installing the project into `.venv` fixed it.

## Agent Rules

- Preserve user focus: use isolated `:98` for game work, not desktop `:0`, unless explicit user handoff is needed.
- Prefix live game CLI calls with `BOBTHEBOT_DISPLAY=:98` and `--backend x11-cv`.
- Record deterministic facts, commands, and state transitions; do not record secrets.
- Treat Cloudflare/CAPTCHA/OTP/2FA as human security handoffs, then resume automation.
- Validate doc claims with commands before writing them as settled facts.

## Architecture Map

- `bobthebot/app.py`: `BotApp` facade that composes config, process supervision, auth, backend registry, and engine.
- `bobthebot/config.py`: environment-driven paths and settings. Default display is `:99`; override with `BOBTHEBOT_DISPLAY`.
- `bobthebot/processes.py`: starts/stops managed Xvfb, standalone RuneLite jar, and visible Chrome auth browser.
- `bobthebot/browser.py`: Chrome DevTools Protocol controller for auth pages, screenshots, visible inputs/buttons, text clicks.
- `bobthebot/auth.py`: semi-agentic Jagex auth state machine. It detects Cloudflare/CAPTCHA/OTP states and returns `needs_user` when a human must act.
- `bobthebot/auth_verification.py`: OTP providers from env var, command, or IMAP.
- `bobthebot/core/engine.py`: threaded task engine and task lifecycle.
- `bobthebot/core/registries.py`: backend registry. Current registered backends are `null` and `x11-cv`.
- `bobthebot/backends/cv.py`: X11 screenshot/raw input backend using ImageMagick `import` and `xdotool`.
- `bobthebot/mcp_server.py`: JSON-RPC 2.0 stdio MCP server.
- `bobthebot/tools/`: modular MCP tool groups. There is no `mcp_tools.py` file now.
- `Scripts/MCPBridge.java`: DreamBot HTTP bridge script, currently legacy/experimental and not wired into the Python backend registry.
- `docs/isolated-bolt-runelite-demo.md`: runbook for the working Bolt + RuneLite path on isolated display `:98`.
- `docs/agent-ops.md`: compact agent runbook and determinism checklist.

## Tool Surface

Inspect live tools with:

```bash
.venv/bin/bobthebot-run tools --renderer none
```

Important current tool names:

- Runtime: `bob_status`, `bob_backend_list`, `bob_runtime_status`, `bob_start_runtime`, `bob_stop_runtime`, `bob_set_backend`
- Engine/tasks: `bob_engine_start`, `bob_engine_stop`, `bob_engine_pause`, `bob_engine_resume`, `bob_task_list`, `bob_task_schema`, `bob_set_task`
- Observation: `bob_observe`, `bob_view`, `bob_player`, `bob_inventory`, `bob_skills`, `bob_nearby`
- Raw input: `bob_click`, `bob_type_text`, `bob_press_key`, `bob_interact`
- Auth: `bob_auth_save_credentials`, `bob_auth_forget_credentials`, `bob_auth_status`, `bob_auth_register_start`, `bob_auth_login_start`, `bob_auth_continue`, `bob_auth_screenshot`, `bob_auth_open`, `bob_auth_verification_check`, `bob_auth_guide_step`, `bob_auth_wait`, `bob_auth_click_text`, `bob_auth_restart_browser`

## Runtime Paths

There are two distinct runtime paths:

1. Managed standalone RuneLite: `bobthebot-run start` starts Xvfb on `BOBTHEBOT_DISPLAY` or `:99`, then launches `osbc/RuneLite.jar`. This does not solve Jagex Account launcher compatibility by itself.
2. Working Bolt/Jagex path: `scripts/isolated_bolt_demo.sh start` starts Xvfb on `:98`, launches local Bolt with `--no-sandbox`, and uses Bolt's saved Jagex session to launch RuneLite. This is the demoable path reached in May 2026.

For Jagex Accounts, standalone RuneLite email/password login failed with the client message that upgraded Jagex Accounts must log in through the Jagex Launcher. Use Bolt for those accounts.

## Auth And Credentials

Repo auth credentials are stored by profile at:

```text
.runtime/auth/credentials.json
```

They are plaintext JSON with file mode `0600`, not encrypted. Do not commit them and do not paste secrets into docs. OTP retrieval priority is:

1. `BOBTHEBOT_EMAIL_CODE`
2. `BOBTHEBOT_EMAIL_CODE_COMMAND`
3. `BOBTHEBOT_IMAP_*`

Live Jagex auth may require Cloudflare, email verification, or 2FA. The intended flow is semi-agentic: the agent opens visible Chrome and reports what the human must do, then resumes after the human completes the security step. Do not try to bypass CAPTCHA/security checks.

## Bolt Demo Facts

Known good state reached on 2026-05-16/17:

- Isolated display: `:98`
- Launcher: Bolt `0.20.6` extracted under `.runtime/bolt/bolt-launcher/bolt`
- Required launch flag: `--no-sandbox`
- Bolt session storage: `~/.local/share/bolt-launcher/`
- Jagex account label seen in Bolt: `MyNameIsBobbbbbbbb`
- OSRS display name chosen during setup: `Kaanfoxwalk`
- Free world selected after members-only warning: `301`
- End state: in-game tutorial/start area with prompt to click the Gielinor Guide

The saved Bolt session is outside the repo. If `~/.local/share/bolt-launcher/creds` is missing or invalid, relaunch Bolt visibly on the user's desktop, let the user complete login/security checks, then move back to isolated `:98`.

## Verification Commands

Low-risk checks:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m radon cc bobthebot/ -s -a
.venv/bin/python -m bobthebot.cli check --renderer none
bash -n scripts/isolated_bolt_demo.sh
scripts/isolated_bolt_demo.sh status
```

System prerequisites for the Bolt demo:

```bash
command -v Xvfb
command -v import
command -v xdotool
command -v chafa
command -v xdpyinfo
java -version
```

## Current Caveats

- README and docs should describe `null` and `x11-cv` as the only registered Python backends unless code changes.
- DreamBot requires `Scripts/MCPBridge.java` running inside DreamBot and currently is not a registered Python backend.
- `BOBTHEBOT_DISPLAY=:98` is mandatory when using repo CLI tools against the isolated Bolt display; otherwise config defaults to `:99`.
- Raw `xdotool type` can be brittle with XTEST/keymap issues. Clicks and screenshots were more reliable in the observed Bolt/RuneLite run.
- Keep user desktop `:0` untouched except when the user explicitly chooses to complete a login/security task in a visible browser or launcher.
