from config import *
from vision import ColorMasks
import time

class Task:
    def __init__(self, name="BaseTask"):
        self.name = name
        self.status = "IDLE"
        self.finished = False

    def on_start(self, engine):
        self.status = "RUNNING"
        print(f"Task {self.name} started.")

    def execute(self, engine):
        return False

    def on_stop(self, engine):
        self.status = "STOPPED"
        self.finished = True
        print(f"Task {self.name} stopped.")

class IdleTask(Task):
    def __init__(self):
        super().__init__("Idle")
    def execute(self, engine):
        return True

class MiningTask(Task):
    def __init__(self):
        super().__init__("Mining")
        self.last_mine = 0

    def execute(self, engine):
        img = engine.vision.capture()
        rocks = engine.vision.detect_color(img, ColorMasks.MAGENTA)
        rock = engine.vision.find_largest(rocks)
        
        if rock is not None:
            now = time.time()
            if now - self.last_mine > 5: # Anti-spam
                center = engine.vision.get_center(rock)
                if center:
                    engine.control.click(center[0], center[1])
                    self.last_mine = now
        return True
