# BobTheBot
**An AI-centered OSRS bot implementation.**

I guess we are attempting to bootstrap a useful/unique OSRS bot implementation without ever manually doing a thing _(ie. never opening a browser, installing the game, knowing how to play, or even seeing the game with human eyes at all!)_.

I've never even played Runescape; I do remember seeings kids in the library play it in like 2007. _Surely that's good enough!_

**This bot will be soley intended to be controlled by an AI agent** like Claude Code, Codex, Gemini CLI, OpenThumb *(my own AI agent harness)*, etc... 

I'm aware it has an active and advanced botting community, and I hear it has fascinating econ-sim elements that would fun to experiement with.

I think a clever design would be a dual-evolution of two separate parts:
 - our bot implementation itself *(not sure the details; assuming CV, lots of mouse interaction and keyboard input, perhaps stochastic or probabilistic aspects, hard & soft waits, heavily abstracted scripting heirarchy, etc.)*
 - MCP server the agent utilizes to interface with & use the bot.

Each of these parts will complement & help to evolve the other, for a unique development loop with clear goals, speedy development, and quality of MCP usage by agents.

## Current Foundation

The project now has a clean Python package in `bobthebot/` that separates the agent-facing interface from the game/runtime implementation:

- `bobthebot.mcp_server` exposes a small MCP-compatible JSON-RPC stdio server.
- `bobthebot.engine` owns lifecycle, task execution, and thread state.
- `bobthebot.backends` contains interchangeable runtime adapters.
- `bobthebot.processes` owns Xvfb/RuneLite/Chromium process supervision.
- `bobthebot.tasks` contains task definitions that should depend on runtime capabilities, not raw subprocesses or CV internals.

The old `osbc/` prototype is retained as reference material and compatibility glue. The new package is the direction for future development.

## Runtime Backends

`null`
: Safe default backend for testing MCP and engine behavior without a game client.

`x11-cv`
: Uses Xvfb/X11 tooling, screenshots, and raw input. This is the natural path for RuneLite plus CV work.

`dreambot`
: Talks to the local Java bridge in `Scripts/MCPBridge.java` at `http://127.0.0.1:19132`. This backend can expose semantic game state when DreamBot is running the bridge script.

## Quick Start

Create an environment and install the package:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

Run tests:

```bash
pytest
```

Inspect local status without launching RuneLite:

```bash
bobthebot-run status
```

Inspect task/backend metadata:

```bash
bobthebot-run backends
bobthebot-run tasks
```

Call an MCP tool without an MCP client:

```bash
bobthebot-run tool --name bob_task_schema --args '{"task": "mining"}'
```

Run the MCP stdio server:

```bash
bobthebot-mcp
```

## MCP Tools

The MCP surface is intentionally small at this stage:

- `bob_status`
- `bob_backend_list`
- `bob_backend_set` / `bob_set_backend`
- `bob_runtime_status`
- `bob_start_runtime`
- `bob_stop_runtime`
- `bob_observe`
- `bob_player`
- `bob_inventory`
- `bob_skills`
- `bob_nearby`
- `bob_task_list`
- `bob_task_schema`
- `bob_engine_start`
- `bob_engine_stop`
- `bob_engine_pause`
- `bob_engine_resume`
- `bob_set_task`
- `bob_task_set`
- `bob_interact`
- `bob_click`
- `bob_type_text`
- `bob_press_key`
- `bob_auth_save_credentials`
- `bob_auth_forget_credentials`
- `bob_auth_status`
- `bob_auth_register_start`
- `bob_auth_login_start`
- `bob_auth_continue`
- `bob_auth_screenshot`
- `bob_auth_open`
- `bob_auth_verification_check`

## Auth Automation

BobTheBot has a Chrome DevTools Protocol auth layer for agent-driven registration/login:

```bash
bobthebot-run tool --name bob_auth_save_credentials --args '{"profile":"main","email":"you@example.com","password":"plaintext"}'
bobthebot-run tool --name bob_auth_register_start --args '{"profile":"main","display_name":"Bob","submit":true}'
bobthebot-run tool --name bob_auth_continue --args '{"profile":"main","email_code":"123456"}'
bobthebot-run auth-view --profile main --view-size 100x40
```

The implementation uses `google-chrome` first, then Chromium fallbacks. Credentials are intentionally stored as plaintext under `.runtime/auth/credentials.json` for speed and agent reuse, with password redaction in tool outputs. CAPTCHA/security checks are detected and surfaced with state/screenshot data rather than bypassed.

`auth-view` captures the current auth browser screenshot and renders it inline with `chafa` when available. It still prints JSON with the screenshot path, so agents can parse the result while humans can see the page state in-terminal.

Email-code automation checks providers in this order:

- `BOBTHEBOT_EMAIL_CODE` or `BOBTHEBOT_EMAIL_CODE_<PROFILE>` for direct env-var injection.
- `BOBTHEBOT_EMAIL_CODE_COMMAND` for a local command that prints a 6-8 digit code. The command receives `BOBTHEBOT_PROFILE`, `BOBTHEBOT_EMAIL`, and `BOBTHEBOT_PURPOSE`.
- IMAP via `BOBTHEBOT_IMAP_HOST`, `BOBTHEBOT_IMAP_USER`, `BOBTHEBOT_IMAP_PASSWORD`, and optional `BOBTHEBOT_IMAP_MAILBOX`.

Future tools should stay agent-oriented. Prefer stable intent/state tools over dumping every low-level game action into MCP.

Tool inputs are validated at the MCP boundary: required fields, unknown fields, primitive types, enum values, string emptiness, and numeric bounds all fail before runtime code is invoked.

Tasks also own config schemas. `bob_task_list` exposes task metadata, and `bob_task_schema` exposes the exact accepted config for a selected task.

## Development Rules

- Keep task logic independent of CV, DreamBot HTTP, Java, and shell commands.
- Add capabilities to backend adapters first, then let tasks consume those capabilities through narrow methods.
- Keep MCP thin. It should adapt tool calls to `BotApp`/`BotEngine`, not own core behavior.
- Tests must pass without RuneLite, DreamBot, Xvfb, Chromium, or OSRS access.
- Generated logs, PID files, profiles, local jars, and credentials should stay out of Git.



<br/> &nbsp;
<sub>[license](LICENSE)</sub>
