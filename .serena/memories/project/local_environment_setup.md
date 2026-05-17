---
name: local_environment_setup
description: Local tools, env vars, directories, and how to set up development environment
metadata:
  type: project
---

# Local Environment Setup & Tools

## Virtual Environment (Whisper)
**Location**: `$HOME/venvs/whisper/`  
**Setup**:
```bash
source "$HOME/venvs/whisper/bin/activate"
```

**Custom activation** (sets up pip cache + tmp dirs):
```bash
whisper-env() {
  export TMPDIR="$HOME/tmp/pip-tmp"
  export PIP_CACHE_DIR="$HOME/tmp/pip-cache"
  source "$HOME/venvs/whisper/bin/activate"
}
whisper-env
```

## Project Installation
```bash
cd /home/alexander/Proj/BobTheBot
python -m pip install -e '.[dev]'
```

This installs:
- **Runtime deps**: websockets>=12
- **Dev deps**: pytest>=8, radon>=6, pyright
- **Console scripts**: bobthebot-run, bobthebot-mcp

## Available System Tools

| Tool | Path/Command | Use Case | Status |
|---|---|---|---|
| google-chrome | `/usr/bin/google-chrome` | Browser automation | ✅ Available |
| chafa | `chafa` | ASCII/color image rendering | ✅ Available |
| ImageMagick (import) | `import` | Screenshot capture | ✅ Available |
| xdotool | `xdotool` | X11 input (click, type) | ✅ Available |
| xvfb-run | `Xvfb` | Virtual framebuffer | ❌ Not found |
| chromium | `chromium` | Fallback browser | ❌ Not found |
| Python | `python3.11+` | Runtime | ✅ Available |

## Key Directories
| Path | Purpose |
|---|---|
| `~/.config/bobthebot/` | Runtime config, credentials, logs |
| `~/.config/bobthebot/auth/credentials.json` | Saved email/password (chmod 0600) |
| `/tmp/bobthebot-*.log` | Temp logs from CLI |
| `.runtime/` | Local runtime state (git-ignored) |

## Environment Variables (Optional)
```bash
# Browser config
export BOBTHEBOT_BROWSER=/usr/bin/google-chrome  # explicit path (auto-detected if not set)
export BOBTHEBOT_DISPLAY=:99                      # X11 display for headless (default: :99)

# Auth config
export BOBTHEBOT_JAGEX_REGISTER_URL=https://account.jagex.com/en-GB/sign-up
export BOBTHEBOT_JAGEX_LOGIN_URL=https://account.jagex.com/en-GB/login

# OTP code providers (in priority order)
export BOBTHEBOT_EMAIL_CODE=123456                # direct code (highest priority)
export BOBTHEBOT_EMAIL_CODE_COMMAND="my-otp-script"  # shell command
export BOBTHEBOT_IMAP_HOST=imap.gmail.com         # IMAP fallback
export BOBTHEBOT_IMAP_USER=user@gmail.com
export BOBTHEBOT_IMAP_PASSWORD=app-password
export BOBTHEBOT_IMAP_MAILBOX=INBOX

# RuneLite config
export BOBTHEBOT_RUNELITE_JAR=~/.runelite/runelite-launcher.jar
```

## Testing Commands
```bash
# Quick test run
pytest -q

# Single test file
pytest tests/test_auth.py -v

# Single test
pytest tests/test_auth.py::test_guide_step -v

# With coverage
pytest --cov=bobthebot tests/

# Code quality
python -m radon cc bobthebot/ -s -a
python -m radon mi bobthebot/ -s
python -m pyright bobthebot/
```

## CLI Commands
```bash
# Status check
bobthebot-run status

# Start runtime (Xvfb + RuneLite)
bobthebot-run runtime-start

# See current screen (ASCII art, refreshes every 1s)
bobthebot-run see --live

# Check auth status
bobthebot-run auth-status

# Save credentials for a profile
bobthebot-run tool --name bob_auth_save_credentials --args '{"profile":"main","email":"you@example.com","password":"secret"}'

# Call a tool directly
bobthebot-run tool bob_auth_guide_step

# MCP server (JSON-RPC stdin)
bobthebot-run mcp
```

## Headless/Visible Browser
```bash
# Default: visible (headless=False)
# Chrome window opens on your desktop via DISPLAY

# Force headless (only if needed, incompatible with Cloudflare Turnstile)
# Set in config or code: start_browser(headless=True)
```

## Isolated Bolt/RuneLite Setup
For testing without real RuneLite:
```bash
# See isolated-bolt-runelite-demo.md for full setup
# Launched via custom wrapper on DISPLAY :98
export DISPLAY=:98
# (Bolt launcher + login automation used separately)
```

## Debugging Tips
- **Chrome hangs?** Kill manually: `killall -9 chrome`
- **No browser found?** Check `BOBTHEBOT_BROWSER` env var or install google-chrome
- **Credentials missing?** Use `bob_auth_save_credentials` or set `BOBTHEBOT_EMAIL_CODE`
- **Tests fail?** Run `pytest -q` and check fixture setup (FakeBrowser, FakeProcesses)
- **State detection broken?** Use `bob_auth_guide_step` → check screenshot + `visible_buttons`