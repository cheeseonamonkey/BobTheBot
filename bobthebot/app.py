from __future__ import annotations

from .auth import AuthService
from .config import BotConfig, default_config
from .engine import BotEngine
from .processes import ProcessSupervisor
from .registries import BackendRegistry, default_backend_registry


class BotApp:
    def __init__(
        self,
        config: BotConfig | None = None,
        backend_name: str = "null",
        backend_registry: BackendRegistry | None = None,
    ):
        self.config = config or default_config()
        self.backends = backend_registry or default_backend_registry()
        self.processes = ProcessSupervisor(self.config)
        self.auth = AuthService(self.config, self.processes)
        self.engine = BotEngine(self.config, self._make_backend(backend_name))

    def _make_backend(self, name: str):
        return self.backends.create(name, self.config)

    def set_backend(self, name: str) -> dict[str, object]:
        self.engine.backend = self._make_backend(name)
        return {"ok": True, "backend": self.engine.backend.status().to_dict()}

    def list_backends(self) -> dict[str, object]:
        return {"backends": self.backends.describe()}

    def status(self) -> dict[str, object]:
        return {"processes": self.processes.status(), "engine": self.engine.status()}
