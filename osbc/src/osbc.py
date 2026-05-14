import time
import random
import threading
from config import *
from vision import OSBCVision, ColorMasks
from control import OSBCControl
from tasks import Task, IdleTask

class OSBCEngine:
    def __init__(self, display=DISPLAY):
        self.display = display
        self.vision = OSBCVision(display=display)
        self.control = OSBCControl(display=display)
        self.running = False
        self.paused = False
        self.task = IdleTask()
        self.last_tick = 0
        self._thread = None

    def set_task(self, task):
        if self.task:
            self.task.on_stop(self)
        self.task = task
        self.task.on_start(self)

    def start(self):
        if self.running: return
        self.running = True
        self.paused = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("Bot Engine started.")

    def stop(self):
        self.running = False
        if self.task:
            self.task.on_stop(self)
        print("Bot Engine stopped.")

    def pause(self):
        self.paused = True
        print("Bot Engine paused.")

    def resume(self):
        self.paused = False
        print("Bot Engine resumed.")

    def _loop(self):
        while self.running:
            if not self.paused and self.task:
                try:
                    now = time.time()
                    if now - self.last_tick >= TICK_RATE:
                        cont = self.task.execute(self)
                        self.last_tick = now
                        if not cont:
                            print(f"Task {self.task.name} finished.")
                            self.set_task(IdleTask())
                except Exception as e:
                    print(f"Error in task execution: {e}")
                    self.paused = True
            time.sleep(0.1)

    def status(self):
        return {
            "running": self.running,
            "paused": self.paused,
            "task": self.task.name if self.task else "None",
            "task_status": self.task.status if self.task else "IDLE"
        }

# Global Engine Instance
ENGINE = OSBCEngine()
