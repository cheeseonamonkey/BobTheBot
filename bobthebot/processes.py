from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from .config import BotConfig


class ProcessSupervisor:
    def __init__(self, config: BotConfig):
        self.config = config
        self.config.ensure_dirs()

    def _pid_file(self, name: str) -> Path:
        return self.config.runtime_dir / f"{name}.pid"

    def is_running(self, name: str) -> bool:
        pid_file = self._pid_file(name)
        if not pid_file.exists():
            return False
        try:
            os.kill(int(pid_file.read_text().strip()), 0)
            return True
        except (OSError, ValueError):
            pid_file.unlink(missing_ok=True)
            return False

    def _start(self, name: str, cmd: list[str], env: dict[str, str] | None = None) -> bool:
        if self.is_running(name):
            return True
        proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self._pid_file(name).write_text(str(proc.pid))
        return True

    def start_xvfb(self) -> bool:
        cmd = [
            "Xvfb",
            self.config.display,
            "-screen",
            "0",
            f"{self.config.width}x{self.config.height}x{self.config.depth}",
            "-ac",
            "-nolisten",
            "tcp",
        ]
        if not self._start("xvfb", cmd):
            return False
        display_num = self.config.display.removeprefix(":")
        socket_path = Path(f"/tmp/.X11-unix/X{display_num}")
        for _ in range(20):
            if socket_path.exists():
                return True
            time.sleep(0.25)
        return self.is_running("xvfb")

    def start_runelite(self, memory_mb: int = 512) -> bool:
        self.start_xvfb()
        env = os.environ.copy()
        env["DISPLAY"] = self.config.display
        return self._start(
            "runelite",
            ["java", f"-Xmx{memory_mb}m", "-jar", str(self.config.runelite_jar), "--developer-mode"],
            env=env,
        )

    

    def find_browser(self) -> str | None:
        candidates = [
            self.config.browser_executable,
            "google-chrome",
            "chromium",
            "chromium-browser",
        ]
        for candidate in candidates:
            if not candidate:
                continue
            if "/" in candidate:
                if Path(candidate).exists():
                    return candidate
            else:
                resolved = shutil.which(candidate)
                if resolved:
                    return resolved
        return None

    def start_browser(self, url: str | None = None, headless: bool = True) -> bool:
        browser = self.find_browser()
        if not browser:
            raise RuntimeError("No supported browser found. Set BOBTHEBOT_BROWSER or install google-chrome/chromium.")
        env = os.environ.copy()
        if "DISPLAY" not in env and not headless:
            env["DISPLAY"] = self.config.display
        cmd = [
            browser,
            "--no-sandbox",
            "--disable-dev-shm-usage",
            f"--remote-debugging-port={self.config.browser_debug_port}",
            f"--user-data-dir={self.config.browser_profile}",
            f"--window-size={self.config.width},{self.config.height}",
            "--disable-first-run-ui",
            "--no-first-run",
        ]
        if headless:
            cmd.append("--headless=new")
        if url:
            cmd.append(url)
        return self._start("browser", cmd, env=env)

    def stop_all(self) -> None:
        for name in ("browser", "runelite", "xvfb"):
            self.stop_process(name)

    def stop_process(self, name: str) -> None:
        pid_file = self._pid_file(name)
        if not pid_file.exists():
            return
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.3)
            if self.is_running(name):
                os.kill(pid, signal.SIGKILL)
        except (OSError, ValueError):
            pass
        finally:
            pid_file.unlink(missing_ok=True)

    def status(self) -> dict[str, bool]:
        return {name: self.is_running(name) for name in ("xvfb", "runelite", "browser")}
