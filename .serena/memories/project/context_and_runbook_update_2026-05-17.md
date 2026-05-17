# BobTheBot context + runbook update - 2026-05-17

User asked to rehydrate project context after additional Claude work, update docs, and preserve repeatable progress around the live RuneLite/Bolt demo. Serena was initialized and project `/home/alexander/Proj/BobTheBot` is active.

## Broad intent
BobTheBot is an AI-agent-controlled Old School RuneScape automation runtime. The product is both the runtime and the agent-facing MCP/CLI control surface: agents start processes, inspect screenshots/state, guide auth, and send raw/semantic actions. Current practical path is RuneLite through Bolt/Jagex Launcher compatibility on an isolated X display, driven by the `x11-cv` backend.

## Current verified entrypoints
Use the repo venv, not raw system Python:

```bash
cd /home/alexander/Proj/BobTheBot
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/bobthebot-run check
.venv/bin/bobthebot-run tools
.venv/bin/bobthebot-run backends
.venv/bin/bobthebot-mcp
```

During verification, system `python3 -m bobthebot.cli ...` failed with `ModuleNotFoundError: No module named 'websockets'`; installing into `.venv` fixed this. Tests pass: `68 passed in 2.99s`.

## Current architecture facts
- `bobthebot/app.py`: `BotApp` facade.
- `bobthebot/config.py`: env-driven settings; default display is `:99` unless `BOBTHEBOT_DISPLAY` is set.
- `bobthebot/processes.py`: Xvfb, standalone RuneLite jar, visible Chrome auth browser.
- `bobthebot/browser.py`: CDP browser controller.
- `bobthebot/auth.py`: semi-agentic auth; detects Cloudflare/CAPTCHA/OTP/2FA and returns `needs_user`.
- `bobthebot/core/registries.py`: currently registers only `null` and `x11-cv` Python backends.
- `bobthebot/tools/`: modular MCP tool registry. There is no `mcp_tools.py` now.
- `Scripts/MCPBridge.java`: DreamBot HTTP bridge code exists, but DreamBot is legacy/experimental and not registered as a Python backend.

## Important tool names
Runtime tools are `bob_status`, `bob_backend_list`, `bob_runtime_status`, `bob_start_runtime`, `bob_stop_runtime`, `bob_set_backend`. Do not use stale names like `bob_runtime_start`, `bob_runtime_stop`, or `bob_backend_set`.

## Bolt/RuneLite demo state
Working path is documented in `docs/isolated-bolt-runelite-demo.md` and helper script `scripts/isolated_bolt_demo.sh`.

Known good state:
- Isolated display: `:98`
- Bolt binary: `.runtime/bolt/bolt-launcher/bolt`
- Bolt version: `0.20.6`
- Required launch flag: `--no-sandbox`
- Bolt session data: `~/.local/share/bolt-launcher/`
- Jagex account label shown in Bolt: `MyNameIsBobbbbbbbb`
- OSRS display name accepted: `Kaanfoxwalk`
- Free world selected after members-only warning: `301`
- End state reached: tutorial/start area with prompt to click the Gielinor Guide

Do not document passwords or verification codes. Replay assumes local Bolt session exists. If `~/.local/share/bolt-launcher/creds` is missing/invalid, launch Bolt visibly on the user's desktop only with permission, let the user complete login/security checks, close visible Bolt, then restart isolated `:98`.

## What worked / did not work
Worked: isolated `DISPLAY=:98`, terminal viewing with `import` + `chafa`, repo `x11-cv` `bob_click`, Bolt saved-session auto-login, selecting `New Character`, world `301`, suggested display name.

Did not work: direct standalone RuneLite login for Jagex account credentials; client said upgraded Jagex Accounts need Jagex Launcher. Direct `account.jagex.com` sign-up path was unreliable; working registration URL was `https://www.runescape.com/oldschool/join`. Cloudflare/security checks are user-handoff steps, not automation targets. Raw `xdotool type` was brittle; clicks/screenshots were more reliable.

## Docs changed
- Added `docs/project-context.md`: dense architecture, entrypoints, current backend/tool facts, auth credential behavior, Bolt demo facts, verification commands, caveats.
- Expanded `docs/isolated-bolt-runelite-demo.md`: prereqs, venv install, helper script, verified state, replay steps, what worked/didn't, recovery from scratch, deterministic checklist.
- Updated `README.md`: fixed stale CLI/MCP commands, tool names, backend status, credential location, CV deps, and linked project context.
- Added `scripts/isolated_bolt_demo.sh`: `start|status|capture|watch|stop` helper for isolated Bolt on `:98`.

## Verification performed
```bash
bash -n scripts/isolated_bolt_demo.sh
scripts/isolated_bolt_demo.sh status
.venv/bin/python -m bobthebot.cli check --renderer none
.venv/bin/python -m bobthebot.cli backends --renderer none
.venv/bin/python -m bobthebot.cli tools --renderer none
.venv/bin/python -m pytest -q
```

Observed prerequisites installed: `/usr/bin/Xvfb`, `/usr/bin/xdpyinfo`, `/usr/bin/import`, `/usr/bin/xdotool`, `/usr/bin/chafa`, `/usr/bin/java`, `/usr/bin/google-chrome`. Repo auth credentials file absent, which is okay for Bolt demo because Bolt stores its own session outside the repo.