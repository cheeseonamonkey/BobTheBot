#!/usr/bin/env bash
set -euo pipefail

ROOT="${BOBTHEBOT_ROOT:-/home/alexander/Proj/BobTheBot}"
DISPLAY_ID="${BOBTHEBOT_DEMO_DISPLAY:-:98}"
SIZE="${BOBTHEBOT_DEMO_SIZE:-1000x700x24}"
LOG_DIR="$ROOT/.runtime/logs"
BOLT_BIN="$ROOT/.runtime/bolt/bolt-launcher/bolt"
SCREENSHOT="$LOG_DIR/demo-current.png"
XVFB_PID="$ROOT/.runtime/xvfb-demo.pid"
BOLT_PID="$ROOT/.runtime/bolt-demo.pid"

usage() {
  cat <<USAGE
Usage: scripts/isolated_bolt_demo.sh start|status|capture|watch|stop

Commands:
  start    Start Xvfb on $DISPLAY_ID and Bolt with --no-sandbox.
  status   Show whether Xvfb, Bolt, and the screenshot tools are available.
  capture  Capture $DISPLAY_ID to $SCREENSHOT.
  watch    Repeatedly capture and render $DISPLAY_ID in the terminal with chafa.
  stop     Stop the demo Bolt and Xvfb processes started by this script.
USAGE
}

is_pid_running() {
  local file="$1"
  [[ -f "$file" ]] || return 1
  local pid
  pid="$(tr -d '[:space:]' < "$file")"
  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" 2>/dev/null
}

start_xvfb() {
  mkdir -p "$LOG_DIR"
  if is_pid_running "$XVFB_PID"; then
    return 0
  fi
  setsid Xvfb "$DISPLAY_ID" -screen 0 "$SIZE" -ac -nolisten tcp \
    > "$LOG_DIR/xvfb-demo.log" 2>&1 < /dev/null &
  echo "$!" > "$XVFB_PID"
}

start_bolt() {
  if [[ ! -x "$BOLT_BIN" ]]; then
    echo "Missing Bolt binary: $BOLT_BIN" >&2
    echo "Install it from the runbook in docs/isolated-bolt-runelite-demo.md." >&2
    exit 1
  fi
  if is_pid_running "$BOLT_PID"; then
    return 0
  fi
  DISPLAY="$DISPLAY_ID" setsid "$BOLT_BIN" --no-sandbox \
    > "$LOG_DIR/bolt-demo.log" 2>&1 < /dev/null &
  echo "$!" > "$BOLT_PID"
}

capture() {
  mkdir -p "$LOG_DIR"
  DISPLAY="$DISPLAY_ID" import -window root "$SCREENSHOT"
  echo "$SCREENSHOT"
}

status() {
  echo "root=$ROOT"
  echo "display=$DISPLAY_ID"
  echo "bolt=$BOLT_BIN"
  command -v Xvfb >/dev/null && echo "Xvfb=$(command -v Xvfb)" || echo "Xvfb=missing"
  command -v import >/dev/null && echo "import=$(command -v import)" || echo "import=missing"
  command -v xdotool >/dev/null && echo "xdotool=$(command -v xdotool)" || echo "xdotool=missing"
  command -v chafa >/dev/null && echo "chafa=$(command -v chafa)" || echo "chafa=missing"
  command -v xdpyinfo >/dev/null && echo "xdpyinfo_bin=$(command -v xdpyinfo)" || echo "xdpyinfo_bin=missing"
  is_pid_running "$XVFB_PID" && echo "xvfb=running pid=$(cat "$XVFB_PID")" || echo "xvfb=stopped"
  is_pid_running "$BOLT_PID" && echo "bolt=running pid=$(cat "$BOLT_PID")" || echo "bolt=stopped"
  DISPLAY="$DISPLAY_ID" xdpyinfo >/dev/null 2>&1 && echo "xdpyinfo=ok" || echo "xdpyinfo=unavailable"
}

stop_process() {
  local file="$1"
  if is_pid_running "$file"; then
    kill "$(cat "$file")" 2>/dev/null || true
  fi
  rm -f "$file"
}

case "${1:-}" in
  start)
    start_xvfb
    start_bolt
    status
    ;;
  status)
    status
    ;;
  capture)
    capture
    ;;
  watch)
    while true; do
      capture >/dev/null 2>&1 || true
      clear
      chafa --symbols block --size "${BOBTHEBOT_DEMO_VIEW_SIZE:-120x45}" "$SCREENSHOT" 2>/dev/null || true
      echo
      echo "Isolated Bolt demo on DISPLAY=$DISPLAY_ID | $(date) | Ctrl-C to stop"
      sleep "${BOBTHEBOT_DEMO_WATCH_SECONDS:-2}"
    done
    ;;
  stop)
    stop_process "$BOLT_PID"
    stop_process "$XVFB_PID"
    ;;
  *)
    usage
    exit 2
    ;;
esac
