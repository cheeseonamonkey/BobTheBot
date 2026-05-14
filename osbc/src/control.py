import subprocess
import time
import random
import numpy as np

class OSBCControl:
    def __init__(self, display=":99"):
        self.display = display
        self.env = {"DISPLAY": display}

    def _run_cmd(self, cmd):
        subprocess.run(cmd, env=self.env, check=True)

    def click(self, x, y, button=1):
        """Click at (x, y)."""
        self.move_mouse(x, y)
        time.sleep(random.uniform(0.05, 0.15))
        self._run_cmd(["xdotool", "click", str(button)])

    def move_mouse(self, x, y):
        """Move mouse to (x, y) with human-like path (simplified)."""
        # For now, we will use a straight line with a small random offset 
        # to keep it lightweight, or implement a proper WindMouse later.
        self._run_cmd(["xdotool", "mousemove", str(x), str(y)])

    def type_text(self, text):
        """Type text with human-like delays."""
        for char in text:
            self._run_cmd(["xdotool", "type", char])
            time.sleep(random.uniform(0.02, 0.08))

    def press_key(self, key):
        """Press a key."""
        self._run_cmd(["xdotool", "key", key])
