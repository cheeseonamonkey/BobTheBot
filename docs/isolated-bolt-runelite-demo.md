# Isolated Bolt + RuneLite Demo

This is the repeatable path we used to get a playable client without taking over the user's desktop.

## Goal

Run Bolt and RuneLite on an isolated X display, keep the main desktop untouched, and drive the client with screenshots/clicks.

Use this when you want a deterministic replay of the session we reached:

1. Bolt starts on `:98`.
2. Bolt auto-signs into the saved Jagex user.
3. RuneLite launches from Bolt.
4. RuneLite gets through EULA, world select, and character setup.
5. The client reaches the in-game/tutorial screen.

For the compact agent checklist, see [agent-ops.md](agent-ops.md). For broader architecture and project context, see [project-context.md](project-context.md).

## Current verified state

Known good state from the May 2026 run:

- isolated display: `:98`
- Bolt install: `.runtime/bolt/bolt-launcher/bolt`
- Bolt version downloaded: `0.20.6`
- required Bolt flag: `--no-sandbox`
- Bolt session data: `~/.local/share/bolt-launcher/`
- Jagex account label shown in Bolt: `MyNameIsBobbbbbbbb`
- OSRS display name chosen: `Kaanfoxwalk`
- free world selected: `301`
- reached state: in-game tutorial/start area with prompt to click the Gielinor Guide

Do not write passwords or verification codes into this repo. The deterministic replay assumes the local Bolt session is already saved.

## Prereqs

- `Xvfb`
- `java`
- `import` from ImageMagick
- `xdotool`
- `chafa` for terminal viewing

On Debian/Ubuntu, the missing pieces were:

```bash
sudo apt-get update
sudo apt-get install -y xvfb x11-utils imagemagick xdotool chafa default-jre
```

Check before starting:

```bash
command -v Xvfb
command -v xdpyinfo
command -v import
command -v xdotool
command -v chafa
java -version
```

Python dependencies must also be installed into the repo venv:

```bash
cd /home/alexander/Proj/BobTheBot
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

## Bolt install

If Bolt is not already present:

```bash
cd /home/alexander/Proj/BobTheBot
mkdir -p .runtime/bolt
cd .runtime/bolt
curl -L -o Bolt-Linux.zip https://github.com/Adamcake/Bolt/releases/download/0.20.6/Bolt-Linux.zip
unzip -o Bolt-Linux.zip
```

Launch binary:

```bash
.runtime/bolt/bolt-launcher/bolt
```

The archive extracts a self-contained launcher under `.runtime/bolt/bolt-launcher/bolt`.

## Isolated display

Use `:98` for the demo display.

Preferred helper:

```bash
cd /home/alexander/Proj/BobTheBot
scripts/isolated_bolt_demo.sh start
scripts/isolated_bolt_demo.sh status
```

Manual equivalent:

```bash
cd /home/alexander/Proj/BobTheBot
mkdir -p .runtime/logs
setsid Xvfb :98 -screen 0 1000x700x24 -ac -nolisten tcp > .runtime/logs/xvfb-demo.log 2>&1 < /dev/null &
DISPLAY=:98 setsid .runtime/bolt/bolt-launcher/bolt --no-sandbox > .runtime/logs/bolt-demo.log 2>&1 < /dev/null &
```

Check the display:

```bash
DISPLAY=:98 xdpyinfo >/dev/null
```

Expected result: `xdpyinfo` exits `0`, Bolt stays running, and the launcher window exists on `:98`.

## View loop

Preferred terminal viewer:

```bash
cd /home/alexander/Proj/BobTheBot
scripts/isolated_bolt_demo.sh watch
```

Manual terminal viewer:

```bash
cat >/tmp/bob-watch-demo.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
cd /home/alexander/Proj/BobTheBot
while true; do
  DISPLAY=:98 import -window root .runtime/logs/demo-current.png 2>/dev/null || true
  clear
  chafa --symbols block --size 120x45 .runtime/logs/demo-current.png 2>/dev/null || true
  echo
  echo "Headless Bolt demo on DISPLAY=:98 | $(date) | Ctrl-C to stop"
  sleep 2
done
SH
chmod +x /tmp/bob-watch-demo.sh
/tmp/bob-watch-demo.sh
```

What it does:

- copies the current root window from `:98` into `.runtime/logs/demo-current.png`
- renders that image in-terminal with `chafa`
- refreshes every 2 seconds

This is the safest way to watch progress without moving focus on the main desktop.

## Replay Steps

Follow these in order.

### 1. Accept Bolt disclaimer

Expected screen: Bolt warning modal with `I Understand`.

Click:

```bash
BOBTHEBOT_DISPLAY=:98 .venv/bin/python -m bobthebot.cli --backend x11-cv tool bob_click x=500 y=426 --renderer none
```

### 2. Stay on OSRS

Expected screen: Bolt home with `RS3` and `OSRS`.

If needed, click `OSRS`:

```bash
BOBTHEBOT_DISPLAY=:98 .venv/bin/python -m bobthebot.cli --backend x11-cv tool bob_click x=347 y=76 --renderer none
```

### 3. Sign into the saved Jagex user

Expected screen: Bolt home, top-right user menu shows `No user selected`.

Open the user menu:

```bash
BOBTHEBOT_DISPLAY=:98 .venv/bin/python -m bobthebot.cli --backend x11-cv tool bob_click x=792 y=137 --renderer none
```

Select the saved user:

```bash
BOBTHEBOT_DISPLAY=:98 .venv/bin/python -m bobthebot.cli --backend x11-cv tool bob_click x=815 y=206 --renderer none
```

Click `Log In` if needed:

```bash
BOBTHEBOT_DISPLAY=:98 .venv/bin/python -m bobthebot.cli --backend x11-cv tool bob_click x=760 y=201 --renderer none
```

Expected result: Bolt status line says the saved user signed in.

### 4. Select a character

Expected screen: `Character` dropdown says `No characters` or `Select an account`.

Open the dropdown:

```bash
BOBTHEBOT_DISPLAY=:98 .venv/bin/python -m bobthebot.cli --backend x11-cv tool bob_click x=499 y=431 --renderer none
```

If `New Character` appears, choose it:

```bash
BOBTHEBOT_DISPLAY=:98 .venv/bin/python -m bobthebot.cli --backend x11-cv tool bob_click x=472 y=501 --renderer none
```

Expected result: `New Character` is selected.

### 5. Launch RuneLite

Click `Play`:

```bash
BOBTHEBOT_DISPLAY=:98 .venv/bin/python -m bobthebot.cli --backend x11-cv tool bob_click x=486 y=274 --renderer none
```

Expected result: the RuneLite launcher download finishes, then RuneLite opens.

### 6. Accept RuneLite EULA

Expected screen: RuneLite disclaimer modal with `Accept` and `Decline`.

Click `Accept`:

```bash
BOBTHEBOT_DISPLAY=:98 .venv/bin/python -m bobthebot.cli --backend x11-cv tool bob_click x=399 y=412 --renderer none
```

### 7. Start the client

Expected screen: RuneLite welcome page with `Play Now`.

Click `Play Now`:

```bash
BOBTHEBOT_DISPLAY=:98 .venv/bin/python -m bobthebot.cli --backend x11-cv tool bob_click x=479 y=361 --renderer none
```

### 8. Handle world membership

If you see:

`You need a members' account to use this world`

then switch worlds.

Click `Switch World`:

```bash
BOBTHEBOT_DISPLAY=:98 .venv/bin/python -m bobthebot.cli --backend x11-cv tool bob_click x=495 y=377 --renderer none
```

Pick a free world from the left side of the table. In our run, `world 301` worked.

### 9. Finish character setup

Expected screen: display-name prompt.

Enter a short name, then `Look up name`.

If the name is unavailable, click one of the suggestions.

When the name is accepted, click `Set name`.

Then:

1. accept the appearance screen with `Confirm`
2. answer the experience question with the simplest option
3. continue until the in-game/tutorial area appears

## Expected Screens

The run is working if you see these in order:

1. Bolt disclaimer
2. Bolt home
3. RuneLite download splash
4. RuneLite EULA
5. RuneLite `Play Now`
6. RuneLite world selector or membership warning
7. Display-name prompt
8. Character creator
9. Tutorial/start area

## X11 Control Commands

Always point the bot tools at the isolated display:

```bash
BOBTHEBOT_DISPLAY=:98 .venv/bin/python -m bobthebot.cli --backend x11-cv observe --renderer none
BOBTHEBOT_DISPLAY=:98 .venv/bin/python -m bobthebot.cli --backend x11-cv tool bob_click x=483 y=360 --renderer none
```

## What worked

- Running Bolt on isolated `DISPLAY=:98` worked and did not steal focus from the user's desktop.
- Terminal viewing with ImageMagick `import` plus `chafa` worked well enough to drive the session.
- The repo `x11-cv` backend worked for screenshots and `bob_click` when `BOBTHEBOT_DISPLAY=:98` was set.
- Bolt auto-signed into the saved local Jagex session after the user completed login/security checks once.
- Selecting `New Character` in Bolt launched RuneLite successfully.
- Switching to free world `301` resolved the initial members-only world warning.
- Choosing a suggested display name was faster than guessing names. `Kaanfoxwalk` was accepted in the observed run.

## What did not work

- Direct standalone RuneLite login with Jagex-account email/password failed. The client reported that upgraded Jagex Accounts must use the Jagex Launcher.
- The direct `account.jagex.com` sign-up path was unreliable during exploration. The working registration path was `https://www.runescape.com/oldschool/join`.
- Cloudflare/Jagex security checks were not automation-friendly. The practical path was to let the user complete them manually once, then reuse Bolt's saved local session.
- `xdotool type` was less reliable than clicks in the isolated display because of XTEST/keymap behavior. Prefer button clicks and manual user entry for fragile text/security fields.
- Raw `python3 -m bobthebot.cli ...` failed until the project dependencies were installed into `.venv`; use `.venv/bin/python` or activate the venv first.

## Recovery from scratch

If Bolt credentials/session are lost:

1. Stop isolated Bolt: `scripts/isolated_bolt_demo.sh stop`
2. Launch Bolt visibly on the user's desktop only with permission.
3. Have the user complete Jagex login, Cloudflare, email verification, and any 2FA/security prompts.
4. Confirm Bolt shows the saved account.
5. Close visible Bolt.
6. Restart isolated mode: `scripts/isolated_bolt_demo.sh start`
7. Continue from the character dropdown or `Play`.

If the character already exists, select that character in Bolt instead of `New Character`.

## Deterministic replay checklist

1. `.venv` exists and `pip install -e ".[dev]"` has completed.
2. `Xvfb`, `xdpyinfo`, `import`, `xdotool`, `chafa`, and Java are available.
3. `.runtime/bolt/bolt-launcher/bolt` exists.
4. `~/.local/share/bolt-launcher/creds` exists and belongs to the current user.
5. `scripts/isolated_bolt_demo.sh start` reports Xvfb and Bolt running.
6. `scripts/isolated_bolt_demo.sh watch` shows the isolated display in-terminal.
7. Every repo CLI command includes `BOBTHEBOT_DISPLAY=:98` and `--backend x11-cv`.
8. The user desktop `:0` is not used unless the user explicitly needs to handle login/security in a visible app.

## Common failures

- If `python3 -m bobthebot.cli ...` tries `:99`, set `BOBTHEBOT_DISPLAY=:98`.
- If `python3 -m bobthebot.cli ...` cannot import `websockets`, install the repo into `.venv` and use `.venv/bin/python`.
- If `import` or `xdpyinfo` cannot open the display, the Xvfb process died; restart it.
- If Bolt aborts with sandbox errors, relaunch it with `--no-sandbox`.
- If RuneLite stops on `Play Now` with a members-only error, switch worlds.
- If setup stops on display-name entry, use a short available suggestion and confirm it.
- If the launcher says `No characters`, open the character dropdown and look for `New Character`.
- If the character setup keeps a modal open, inspect the screenshot and click the next action button before waiting again.

## Shutdown

```bash
scripts/isolated_bolt_demo.sh stop
```

## Notes

- We used `:98` so the demo could be replayed without touching the user's desktop `:0`.
- The displayed state is reproducible from the saved Bolt credentials in `~/.local/share/bolt-launcher/`.
- `BOBTHEBOT_DISPLAY` is required for the repo's screenshot backend to target the isolated display.
