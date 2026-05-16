from __future__ import annotations

import os
import random
import subprocess
import time
from pathlib import Path
from ..core.models import ActionResult, EntityRef, InventoryState, Observation, RuntimeStatus, SkillsState
from ..config import BotConfig


class X11CvBackend:
    name = "x11-cv"
    capabilities = ("observe", "screenshot", "raw_input")

    def __init__(self, config: BotConfig):
        self.config = config

    @property
    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["DISPLAY"] = self.config.display
        return env

    def status(self) -> RuntimeStatus:
        return RuntimeStatus(
            backend=self.name,
            ready=True,
            detail={"display": self.config.display, "capabilities": self.capabilities},
        )

    def observe(self) -> Observation:
        path = self.screenshot()
        return Observation(source=self.name, data={"screenshot": str(path)})

    def screenshot(self, filename: str = "screenshot.png") -> Path:
        path = self.config.logs_dir / filename
        subprocess.run(["import", "-window", "root", str(path)], env=self.env, check=True)
        return path

    def click(self, x: int, y: int, button: int = 1) -> ActionResult:
        self._run(["xdotool", "mousemove", str(x), str(y)])
        time.sleep(random.uniform(0.05, 0.15))
        self._run(["xdotool", "click", str(button)])
        return ActionResult(True, "click", data={"x": x, "y": y, "button": button})

    def type_text(self, text: str) -> ActionResult:
        for char in text:
            self._run(["xdotool", "type", char])
            time.sleep(random.uniform(0.02, 0.08))
        return ActionResult(True, "type_text", data={"text_len": len(text)})

    def press_key(self, key: str) -> ActionResult:
        self._run(["xdotool", "key", key])
        return ActionResult(True, "press_key", target=key)

    def interact(self, target: EntityRef) -> ActionResult:
        return ActionResult(False, "interact", target=target.name, error="x11-cv backend needs a screen coordinate target")

    def player(self) -> dict[str, str]:
        return {"error": "x11-cv backend has no semantic player state"}

    def inventory(self) -> InventoryState:
        return InventoryState()

    def skills(self) -> SkillsState:
        return SkillsState()

    def nearby(self, kind: str, name: str = "", radius: int = 15) -> dict[str, str]:
        return {"error": "x11-cv backend has no semantic nearby entity index", "kind": kind}

    def _run(self, cmd: list[str]) -> None:
        subprocess.run(cmd, env=self.env, check=True)
