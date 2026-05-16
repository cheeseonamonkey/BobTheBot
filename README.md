# BobTheBot

**An AI-controlled OSRS bot runtime — developed entirely by AI agents, never by hand.**

The goal: bootstrap a working OSRS bot without a human ever opening a browser, installing the game, or seeing it. An agent does all of it through the MCP server.

Two things co-evolve:
- **The bot runtime** — backends, task engine, auth automation, CV pipeline
- **The MCP server** — the agent's interface into the bot

---

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"       # core + tests
pip install -e ".[dev,cv]"    # + computer-vision backend
```

## Quick start

```bash
bobthebot-run doctor          # check deps and paths
bobthebot-run demo-view       # render test image via chafa
bobthebot-run status          # process + engine state
bobthebot-run tools           # list all MCP tools
bobthebot-run start           # launch Xvfb + RuneLite
bobthebot-run observe         # snapshot current game state
bobthebot-run observe --watch 2   # live refresh every 2 s
```

For the repeatable isolated Bolt/RuneLite flow we used, see [docs/isolated-bolt-runelite-demo.md](/home/alexander/Proj/BobTheBot/docs/isolated-bolt-runelite-demo.md).

## Backends

| Name | Description |
|------|-------------|
| `null` | Safe no-game backend for testing (default) |
| `x11-cv` | X11 screenshot + raw input (requires `[cv]`) |
| `dreambot` | Semantic API via local DreamBot HTTP bridge |

Select with `--backend NAME` on any command.

## MCP server

Exposes all tools over stdio (JSON-RPC 2.0) for use with Claude Desktop, Claude Code, or any MCP client:

```bash
bobthebot-mcp
```

Run `bobthebot-run tools` for the full tool list.

## CLI reference

```
bobthebot-run COMMAND [target] [KEY=VALUE ...] [options]

Commands:
  status           Process + engine status
  start / stop     Start or stop Xvfb + RuneLite
  backends         List available backends
  tasks            List available bot tasks
  tools            List MCP tools
  tool NAME        Call an MCP tool (e.g. tool bob_set_task task=mining)
  observe          Snapshot game state (--watch N for live loop)
  view PATH        Render an image file via chafa
  demo-view        Generate + render a test image
  auth-status      Auth browser state
  auth-view        Screenshot the auth browser
  script PATH      Run a Python script with app in scope
  doctor           Check dependencies and paths

Options:
  --backend        null | x11-cv | dreambot  (default: null)
  --renderer       auto | chafa | none
  --view-size      WIDTHxHEIGHT for chafa  (default: 100x40)
  --watch SECS     Live-loop interval for observe
  --profile        Auth profile name  (default: default)
  --args JSON      JSON arguments for tool command
```

Exit code is 1 when the result contains `"error"` or `"ok": false`.

## Auth

Credentials live at `.runtime/auth/credentials.json`.

```bash
bobthebot-run tool bob_auth_save_credentials email=you@example.com password=hunter2
bobthebot-run auth-status
bobthebot-run tool bob_auth_login_start email=you@example.com password=hunter2
bobthebot-run tool bob_auth_continue email_code=123456
bobthebot-run auth-view   # renders browser screenshot in-terminal
```

Email-code providers (checked in order): `BOBTHEBOT_EMAIL_CODE` env var → `BOBTHEBOT_EMAIL_CODE_COMMAND` shell command → IMAP (`BOBTHEBOT_IMAP_HOST/USER/PASSWORD`).

## Dev rules

- Task logic must not depend on CV, DreamBot HTTP, Java, or shell commands directly — use backend capabilities.
- MCP stays thin: it adapts calls to `BotApp`/`BotEngine`, not own core behavior.
- Tests must pass without RuneLite, Xvfb, DreamBot, or a browser.

```bash
pytest
```

## Dependencies

- Python ≥ 3.11
- `chafa` — terminal image rendering (`apt install chafa`)
- `google-chrome` — auth browser automation
- `java` — RuneLite
- `Xvfb` — virtual display (`apt install xvfb`)

---

<sub>[license](LICENSE)</sub>
