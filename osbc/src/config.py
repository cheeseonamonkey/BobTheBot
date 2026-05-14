import os
from pathlib import Path

# Project Roots
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
LOGS = ROOT / "logs"
CONFIG = ROOT / "config"
SCRIPTS = ROOT / "scripts"

# Display Settings
DISPLAY = os.getenv("OSBC_DISPLAY", ":99")
WIDTH = 800
HEIGHT = 600
DEPTH = 24

# Process Paths
RUNELITE_JAR = ROOT / "RuneLite.jar"
CHROMIUM_PROFILE = CONFIG / "chromium-profile"
XVFB_PID = LOGS / "xvfb.pid"
RUNELITE_PID = LOGS / "runelite.pid"
CHROMIUM_PID = LOGS / "chromium.pid"

# Bot Settings
TICK_RATE = 0.5  # Seconds between logic ticks
MOUSE_SPEED = 1.0 # Multiplier for human-like movement
OCR_ENABLED = False # Keep it lightweight

def ensure_dirs():
    for d in [LOGS, CONFIG, SCRIPTS]:
        d.mkdir(parents=True, exist_ok=True)

ensure_dirs()
