import os
import subprocess
import time
import signal
import sys
from config import *

class OSBCLauncher:
    def __init__(self):
        self.env = os.environ.copy()
        self.env["DISPLAY"] = DISPLAY

    def is_running(self, pid_file):
        if not pid_file.exists():
            return False
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            pid_file.unlink(missing_ok=True)
            return False

    def start_xvfb(self):
        if self.is_running(XVFB_PID):
            return True
        print(f"Starting Xvfb on {DISPLAY} ({WIDTH}x{HEIGHT})...")
        cmd = ["Xvfb", DISPLAY, "-screen", "0", f"{WIDTH}x{HEIGHT}x{DEPTH}", "-ac", "-nolisten", "tcp"]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        XVFB_PID.write_text(str(proc.pid))
        
        # Deterministic wait for Xvfb socket
        display_num = DISPLAY[1:]
        socket_path = f"/tmp/.X11-unix/X{display_num}"
        for _ in range(10):
            if os.path.exists(socket_path):
                print("Xvfb is ready.")
                return True
            time.sleep(0.5)
        return self.is_running(XVFB_PID)

    def start_runelite(self, memory_mb=512):
        if self.is_running(RUNELITE_PID):
            return True
        self.start_xvfb() # Ensure display is up
        print(f"Launching RuneLite ({memory_mb}MB heap)...")
        cmd = ["java", f"-Xmx{memory_mb}m", "-jar", str(RUNELITE_JAR), "--developer-mode"]
        proc = subprocess.Popen(cmd, env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        RUNELITE_PID.write_text(str(proc.pid))
        
        # Deterministic wait for window (optional but good)
        print("Waiting for RuneLite process to stabilize...")
        time.sleep(5) 
        return True

    def start_chromium(self, url=None):
        if self.is_running(CHROMIUM_PID):
            return True
        print("Launching Chromium for auth...")
        cmd = [
            "chromium",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--remote-debugging-port=9222",
            f"--user-data-dir={CHROMIUM_PROFILE}",
            f"--window-size={WIDTH},{HEIGHT}"
        ]
        if url: cmd.append(url)
        proc = subprocess.Popen(cmd, env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        CHROMIUM_PID.write_text(str(proc.pid))
        return True

    def stop_all(self):
        for pf in [CHROMIUM_PID, RUNELITE_PID, XVFB_PID]:
            if pf.exists():
                try:
                    pid = int(pf.read_text().strip())
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.5)
                    if self.is_running(pf):
                        os.kill(pid, signal.SIGKILL)
                except: pass
                pf.unlink(missing_ok=True)
        print("All processes stopped.")

    def status(self):
        return {
            "xvfb": self.is_running(XVFB_PID),
            "runelite": self.is_running(RUNELITE_PID),
            "chromium": self.is_running(CHROMIUM_PID)
        }

if __name__ == "__main__":
    launcher = OSBCLauncher()
    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action == "start":
            launcher.start_xvfb()
            launcher.start_runelite()
        elif action == "stop":
            launcher.stop_all()
        elif action == "status":
            print(launcher.status())
    else:
        launcher.start_xvfb()
        launcher.start_runelite()
        print(launcher.status())
