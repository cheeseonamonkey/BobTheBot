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

## Prereqs

- `Xvfb`
- `java`
- `import` from ImageMagick
- `xdotool`
- `chafa` for terminal viewing

On Debian/Ubuntu, the missing pieces were:

```bash
sudo apt-get update
sudo apt-get install -y xvfb imagemagick xdotool chafa
```

Check before starting:

```bash
command -v Xvfb
command -v import
command -v xdotool
command -v chafa
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

```bash
cd /home/alexander/Proj/BobTheBot
setsid Xvfb :98 -screen 0 1000x700x24 -ac -nolisten tcp > .runtime/logs/xvfb-demo.log 2>&1 < /dev/null &
DISPLAY=:98 setsid .runtime/bolt/bolt-launcher/bolt --no-sandbox > .runtime/logs/bolt-demo.log 2>&1 < /dev/null &
```

Check the display:

```bash
DISPLAY=:98 xdpyinfo >/dev/null
```

Expected result: `xdpyinfo` exits `0`, Bolt stays running, and the launcher window exists on `:98`.

## View loop

Terminal viewer:

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
BOBTHEBOT_DISPLAY=:98 python3 -m bobthebot.cli --backend x11-cv tool bob_click x=500 y=426 --renderer none
```

### 2. Stay on OSRS

Expected screen: Bolt home with `RS3` and `OSRS`.

If needed, click `OSRS`:

```bash
BOBTHEBOT_DISPLAY=:98 python3 -m bobthebot.cli --backend x11-cv tool bob_click x=347 y=76 --renderer none
```

### 3. Sign into the saved Jagex user

Expected screen: Bolt home, top-right user menu shows `No user selected`.

Open the user menu:

```bash
BOBTHEBOT_DISPLAY=:98 python3 -m bobthebot.cli --backend x11-cv tool bob_click x=792 y=137 --renderer none
```

Select the saved user:

```bash
BOBTHEBOT_DISPLAY=:98 python3 -m bobthebot.cli --backend x11-cv tool bob_click x=815 y=206 --renderer none
```

Click `Log In` if needed:

```bash
BOBTHEBOT_DISPLAY=:98 python3 -m bobthebot.cli --backend x11-cv tool bob_click x=760 y=201 --renderer none
```

Expected result: Bolt status line says the saved user signed in.

### 4. Select a character

Expected screen: `Character` dropdown says `No characters` or `Select an account`.

Open the dropdown:

```bash
BOBTHEBOT_DISPLAY=:98 python3 -m bobthebot.cli --backend x11-cv tool bob_click x=499 y=431 --renderer none
```

If `New Character` appears, choose it:

```bash
BOBTHEBOT_DISPLAY=:98 python3 -m bobthebot.cli --backend x11-cv tool bob_click x=472 y=501 --renderer none
```

Expected result: `New Character` is selected.

### 5. Launch RuneLite

Click `Play`:

```bash
BOBTHEBOT_DISPLAY=:98 python3 -m bobthebot.cli --backend x11-cv tool bob_click x=486 y=274 --renderer none
```

Expected result: the RuneLite launcher download finishes, then RuneLite opens.

### 6. Accept RuneLite EULA

Expected screen: RuneLite disclaimer modal with `Accept` and `Decline`.

Click `Accept`:

```bash
BOBTHEBOT_DISPLAY=:98 python3 -m bobthebot.cli --backend x11-cv tool bob_click x=399 y=412 --renderer none
```

### 7. Start the client

Expected screen: RuneLite welcome page with `Play Now`.

Click `Play Now`:

```bash
BOBTHEBOT_DISPLAY=:98 python3 -m bobthebot.cli --backend x11-cv tool bob_click x=479 y=361 --renderer none
```

### 8. Handle world membership

If you see:

`You need a members' account to use this world`

then switch worlds.

Click `Switch World`:

```bash
BOBTHEBOT_DISPLAY=:98 python3 -m bobthebot.cli --backend x11-cv tool bob_click x=495 y=377 --renderer none
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
BOBTHEBOT_DISPLAY=:98 python3 -m bobthebot.cli --backend x11-cv observe --renderer none
BOBTHEBOT_DISPLAY=:98 python3 -m bobthebot.cli --backend x11-cv tool bob_click x=483 y=360 --renderer none
```

## Common failures

- If `python3 -m bobthebot.cli ...` tries `:99`, set `BOBTHEBOT_DISPLAY=:98`.
- If `import` or `xdpyinfo` cannot open the display, the Xvfb process died; restart it.
- If Bolt aborts with sandbox errors, relaunch it with `--no-sandbox`.
- If RuneLite stops on `Play Now` with a members-only error, switch worlds.
- If setup stops on display-name entry, use a short available suggestion and confirm it.
- If the launcher says `No characters`, open the character dropdown and look for `New Character`.
- If the character setup keeps a modal open, inspect the screenshot and click the next action button before waiting again.

## Shutdown

```bash
pkill -f '.runtime/bolt/bolt-launcher/bolt' || true
pkill -f 'Xvfb :98' || true
```

## Notes

- We used `:98` so the demo could be replayed without touching the user's desktop `:0`.
- The displayed state is reproducible from the saved Bolt credentials in `.local/share/bolt-launcher/`.
- `BOBTHEBOT_DISPLAY` is required for the repo's screenshot backend to target the isolated display.
