from __future__ import annotations

import threading
import time
from typing import Any

from .backends.base import BotBackend
from .config import BotConfig
from .tasks import IdleTask, Task, TaskRegistry, default_task_registry


class BotEngine:
    def __init__(self, config: BotConfig, backend: BotBackend, task_registry: TaskRegistry | None = None):
        self.config = config
        self.backend = backend
        self.task_registry = task_registry or default_task_registry()
        self.running = False
        self.paused = False
        self.task: Task = IdleTask()
        self.last_result: dict[str, Any] | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self.running:
                return
            self.running = True
            self.paused = False
            self.task.on_start(self)
            self._thread = threading.Thread(target=self._loop, name="bobthebot-engine", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self.running = False
            self.task.on_stop(self)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(self.config.tick_rate * 2, 0.2))

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def set_task(self, name: str, **kwargs: Any) -> None:
        next_task = self.task_registry.create(name, kwargs)
        self._ensure_backend_supports(next_task)
        with self._lock:
            self.task.on_stop(self)
            self.task = next_task
            if self.running:
                self.task.on_start(self)

    def status(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "paused": self.paused,
            "task": self.task.name,
            "task_status": self.task.status,
            "backend": self.backend.status().to_dict(),
            "last_result": self.last_result,
        }

    def observe(self) -> dict[str, Any]:
        return self.backend.observe().to_dict()

    def tasks(self) -> list[dict[str, object]]:
        return self.task_registry.describe()

    def task_schema(self, name: str) -> dict[str, Any]:
        return self.task_registry.schema_for(name)

    def _ensure_backend_supports(self, task: Task) -> None:
        capabilities = set(getattr(self.backend, "capabilities", ()))
        missing = [item for item in task.required_capabilities if item not in capabilities]
        if missing:
            raise ValueError(
                f"Task {task.name} requires backend capabilities {missing}; "
                f"current backend {self.backend.name} has {sorted(capabilities)}"
            )

    def _loop(self) -> None:
        while self.running:
            if not self.paused:
                try:
                    keep_running = self.task.execute(self)
                    if not keep_running:
                        self.set_task("idle")
                except Exception as exc:
                    self.paused = True
                    self.last_result = {"error": str(exc)}
            time.sleep(self.config.tick_rate)
