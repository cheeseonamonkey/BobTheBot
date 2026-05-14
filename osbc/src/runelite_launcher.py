import subprocess
import os
import time

class RuneLiteLauncher:
    def __init__(self, display=":99", jar_path="RuneLite.jar"):
        self.display = display
        self.jar_path = jar_path
        self.env = os.environ.copy()
        self.env["DISPLAY"] = display

    def start(self, memory_mb=512):
        """Start RuneLite with limited memory."""
        print(f"Starting RuneLite on {self.display} with {memory_mb}MB heap...")
        cmd = [
            "java",
            f"-Xmx{memory_mb}m",
            "-jar", self.jar_path,
            "--developer-mode",  # Useful for some plugins
            "--off-heap-canvas"  # Potential performance/memory benefit
        ]
        # Start in background
        proc = subprocess.Popen(cmd, env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return proc

if __name__ == "__main__":
    launcher = RuneLiteLauncher()
    launcher.start()
