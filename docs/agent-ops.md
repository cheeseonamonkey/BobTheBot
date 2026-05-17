# Agent Ops

Read this first when resuming BobTheBot work. It is intentionally dense and current as of 2026-05-17.

## Intent

BobTheBot is an agent-operated OSRS runtime plus MCP/CLI control layer. Agents should be able to start runtime pieces, inspect state, drive auth/game clicks, and hand off only explicit security checks to the user.

Current demo path: Bolt launches RuneLite on isolated X display `:98`; repo tools observe/click it through `x11-cv`.

## Hard Rules

- Do not record passwords, OTPs, session tokens, or Bolt credential contents in repo docs.
- Do not control the user's desktop `:0` unless the user explicitly asks or must complete a security/login step.
- Use `.venv/bin/python` or `.venv/bin/bobthebot-run`; raw `python3` may miss `websockets`.
- Set `BOBTHEBOT_DISPLAY=:98` for every repo CLI call that targets isolated Bolt.
- Use `--backend x11-cv` for screenshots/clicks against the live isolated client.
- Treat CAPTCHA, Cloudflare, email verification, and 2FA as user handoff states.
- Keep DreamBot references legacy/experimental unless a Python backend is registered again.

## Known Good Baseline

```bash
cd /home/alexander/Proj/BobTheBot
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```

Expected test baseline: `68 passed`.

Required system tools for the Bolt demo:

```bash
command -v Xvfb
command -v xdpyinfo
command -v import
command -v xdotool
command -v chafa
command -v java
```

## Current Entry Points

```bash
.venv/bin/bobthebot-run check
.venv/bin/bobthebot-run status
.venv/bin/bobthebot-run backends
.venv/bin/bobthebot-run tools --renderer none
.venv/bin/bobthebot-run see --live
.venv/bin/bobthebot-mcp
```

Module equivalents:

```bash
.venv/bin/python -m bobthebot.cli check --renderer none
.venv/bin/python -m bobthebot.mcp_server
```

## Current Backends

- `null`: safe fake backend for tests/tool schema work.
- `x11-cv`: real X11 screenshot and raw input backend using ImageMagick `import` and `xdotool`.
- DreamBot: Java bridge file exists at `Scripts/MCPBridge.java`, but no registered Python backend currently exposes it.

Validate before documenting backend behavior:

```bash
.venv/bin/python -m bobthebot.cli backends --renderer none
```

## Current Tool Names

Runtime:

```text
bob_status, bob_backend_list, bob_runtime_status, bob_start_runtime, bob_stop_runtime, bob_set_backend
```

Auth:

```text
bob_auth_save_credentials, bob_auth_forget_credentials, bob_auth_status,
bob_auth_register_start, bob_auth_login_start, bob_auth_continue,
bob_auth_screenshot, bob_auth_open, bob_auth_verification_check,
bob_auth_guide_step, bob_auth_wait, bob_auth_click_text, bob_auth_restart_browser
```

Observe/input:

```text
bob_observe, bob_view, bob_player, bob_inventory, bob_skills, bob_nearby,
bob_click, bob_type_text, bob_press_key, bob_interact
```

Do not use stale names such as `bob_runtime_start`, `bob_runtime_stop`, or `bob_backend_set`.

## State Locations

- Repo runtime: `.runtime/`
- Repo logs/screenshots: `.runtime/logs/`
- Repo auth credential store: `.runtime/auth/credentials.json`
- Standalone RuneLite jar: `osbc/RuneLite.jar`
- Bolt binary: `.runtime/bolt/bolt-launcher/bolt`
- Bolt session/profile: `~/.local/share/bolt-launcher/`
- Isolated demo screenshot: `.runtime/logs/demo-current.png`

Repo auth credentials are plaintext JSON with chmod `0600`. Bolt session state is outside the repo and is required for deterministic Jagex-account replay.

## Runtime Choice

Use managed standalone RuneLite only for process/backend work:

```bash
.venv/bin/bobthebot-run start
.venv/bin/bobthebot-run stop
```

Use isolated Bolt for the real Jagex Account demo:

```bash
scripts/isolated_bolt_demo.sh start
scripts/isolated_bolt_demo.sh watch
```

Standalone RuneLite email/password login failed for Jagex Accounts; the client required Jagex Launcher. Bolt is the current launcher-compatible path.

## Isolated Bolt Replay

Minimal deterministic loop:

```bash
cd /home/alexander/Proj/BobTheBot
scripts/isolated_bolt_demo.sh start
scripts/isolated_bolt_demo.sh status
scripts/isolated_bolt_demo.sh watch
```

Click/observe with:

```bash
BOBTHEBOT_DISPLAY=:98 .venv/bin/python -m bobthebot.cli --backend x11-cv observe --renderer none
BOBTHEBOT_DISPLAY=:98 .venv/bin/python -m bobthebot.cli --backend x11-cv tool bob_click x=500 y=426 --renderer none
```

Known good facts:

- Bolt `0.20.6`
- `--no-sandbox` required
- Jagex account label seen: `MyNameIsBobbbbbbbb`
- OSRS display name accepted: `Kaanfoxwalk`
- free world used: `301`
- end state reached: tutorial/start area

## Auth Pattern

Agent loop:

1. Start visible browser or Bolt.
2. Fill/click only normal fields/buttons.
3. On Cloudflare/CAPTCHA/OTP/2FA, stop and ask user to act.
4. Resume with `bob_auth_guide_step` or Bolt screenshot after user finishes.
5. Record page states and fixes, never secrets.

Registration path that worked during exploration:

```text
https://www.runescape.com/oldschool/join
```

Direct `account.jagex.com` sign-up paths were unreliable during this run.

## Determinism Checks

Before claiming a runbook works:

```bash
bash -n scripts/isolated_bolt_demo.sh
scripts/isolated_bolt_demo.sh status
.venv/bin/python -m bobthebot.cli check --renderer none
.venv/bin/python -m bobthebot.cli backends --renderer none
.venv/bin/python -m bobthebot.cli tools --renderer none
.venv/bin/python -m pytest -q
```

For live display work also confirm:

```bash
BOBTHEBOT_DISPLAY=:98 .venv/bin/python -m bobthebot.cli --backend x11-cv observe --renderer none
```

## Common Failure Modes

- `ModuleNotFoundError: websockets`: install into `.venv` and use `.venv/bin/python`.
- CLI observes `:99`: export or prefix `BOBTHEBOT_DISPLAY=:98`.
- `xdpyinfo=unavailable`: Xvfb is not running or wrong display.
- Bolt exits immediately: relaunch with `--no-sandbox`.
- Members-only error after `Play Now`: switch to a free world; `301` worked.
- No Bolt character: open character dropdown and choose `New Character`, or select existing character.
- Text entry flakes: prefer clicks/suggestions; `xdotool type` was less reliable than clicks.
- Repo credentials absent: normal for Bolt replay; Bolt session is in `~/.local/share/bolt-launcher/`.

## Update Protocol

When code changes alter commands, paths, tools, or runtime behavior:

1. Update this file.
2. Update [project-context.md](project-context.md) if architecture or persistent facts changed.
3. Update [isolated-bolt-runelite-demo.md](isolated-bolt-runelite-demo.md) if live replay changed.
4. Run the determinism checks above.
5. Write a Serena memory with date, exact changed facts, and verification output.
