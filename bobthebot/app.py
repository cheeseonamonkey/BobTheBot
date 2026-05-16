from __future__ import annotations

from typing import Any

from .auth import AuthService
from .backends.base import BotBackend
from .config import BotConfig, default_config
from .core.engine import BotEngine
from .core.models import EntityRef, compact_dict
from .core.registries import BackendRegistry, default_backend_registry
from .processes import ProcessSupervisor


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

    # ── Internal helpers ──────────────────────────────────────────────────

    def _make_backend(self, name: str) -> BotBackend:
        return self.backends.create(name, self.config)

    # ── Status ────────────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        return {"processes": self.processes.status(), "engine": self.engine.status()}

    def backend_status(self) -> dict[str, Any]:
        return self.engine.backend.status().to_dict()

    # ── Runtime lifecycle ─────────────────────────────────────────────────

    def start_runtime(self) -> dict[str, Any]:
        return {
            "xvfb": self.processes.start_xvfb(),
            "runelite": self.processes.start_runelite(),
            "status": self.processes.status(),
        }

    def stop_runtime(self) -> dict[str, Any]:
        self.engine.stop()
        self.processes.stop_all()
        return {"ok": True}

    # ── Backend selection ─────────────────────────────────────────────────

    def backend_names(self) -> list[str]:
        return list(self.backends.names())

    def list_backends(self) -> dict[str, Any]:
        return {"backends": self.backends.describe()}

    def set_backend(self, name: str) -> dict[str, Any]:
        self.engine.backend = self._make_backend(name)
        return {"ok": True, "backend": self.engine.backend.status().to_dict()}

    # ── Engine lifecycle ──────────────────────────────────────────────────

    def engine_start(self) -> dict[str, Any]:
        self.engine.start()
        return self.engine.status()

    def engine_stop(self) -> dict[str, Any]:
        self.engine.stop()
        return self.engine.status()

    def engine_pause(self) -> dict[str, Any]:
        self.engine.pause()
        return self.engine.status()

    def engine_resume(self) -> dict[str, Any]:
        self.engine.resume()
        return self.engine.status()

    # ── Tasks ─────────────────────────────────────────────────────────────

    def task_names(self) -> list[str]:
        return self.engine.task_registry.names()

    def list_tasks(self) -> list[dict[str, Any]]:
        return self.engine.tasks()

    def task_schema(self, name: str) -> dict[str, Any]:
        return self.engine.task_schema(name)

    def set_task(self, name: str, **kwargs: Any) -> dict[str, Any]:
        self.engine.set_task(name, **kwargs)
        return self.engine.status()

    # ── Observation ───────────────────────────────────────────────────────

    def observe(self) -> dict[str, Any]:
        return self.engine.observe()

    def player(self) -> dict[str, Any]:
        return compact_dict(self.engine.backend.player())

    def inventory(self) -> dict[str, Any]:
        return compact_dict(self.engine.backend.inventory())

    def skills(self) -> dict[str, Any]:
        return compact_dict(self.engine.backend.skills())

    def nearby(self, kind: str, name: str = "", radius: int = 15) -> dict[str, Any]:
        return self.engine.backend.nearby(kind=kind, name=name, radius=radius)

    # ── Raw input ─────────────────────────────────────────────────────────

    def click(self, x: int, y: int, button: int = 1) -> dict[str, Any]:
        return self.engine.backend.click(x, y, button).to_dict()

    def type_text(self, text: str) -> dict[str, Any]:
        return self.engine.backend.type_text(text).to_dict()

    def press_key(self, key: str) -> dict[str, Any]:
        return self.engine.backend.press_key(key).to_dict()

    def interact(self, target: EntityRef) -> dict[str, Any]:
        return self.engine.backend.interact(target).to_dict()

    # ── Capability guard ──────────────────────────────────────────────────

    def require_capability(self, capability: str) -> None:
        capabilities = set(getattr(self.engine.backend, "capabilities", ()))
        if capability not in capabilities:
            raise ValueError(
                f"Backend {self.engine.backend.name} does not support {capability}; "
                f"available capabilities: {sorted(capabilities)}"
            )

    # ── Auth ──────────────────────────────────────────────────────────────

    def auth_status(self, profile: str = "default") -> dict[str, Any]:
        return self.auth.status(profile)

    def auth_save_credentials(self, profile: str, email: str, password: str) -> dict[str, Any]:
        return self.auth.save_credentials(profile, email, password)

    def auth_forget_credentials(self, profile: str) -> dict[str, Any]:
        return self.auth.forget_credentials(profile)

    def auth_login_start(self, **kwargs: Any) -> dict[str, Any]:
        return self.auth.login_start(**kwargs)

    def auth_register_start(self, **kwargs: Any) -> dict[str, Any]:
        return self.auth.register_start(**kwargs)

    def auth_continue(self, **kwargs: Any) -> dict[str, Any]:
        return self.auth.continue_flow(**kwargs)

    def auth_screenshot(self, profile: str = "default") -> dict[str, Any]:
        return self.auth.screenshot(profile)

    def auth_open(self, url: str) -> dict[str, Any]:
        return self.auth.open(url)

    def auth_verification_check(self, profile: str = "default", purpose: str = "auth") -> dict[str, Any]:
        return self.auth.verification_check(profile, purpose)

    def auth_guide_step(self, profile: str = "default") -> dict[str, Any]:
        return self.auth.guide_step(profile)

    def auth_wait(self, target_states: list[str], timeout: float = 30.0) -> dict[str, Any]:
        return self.auth.wait_for_state(target_states, timeout=timeout)

    def auth_click_text(self, text: str) -> dict[str, Any]:
        return self.auth.click_text(text)

    def auth_restart_browser(self, url: str | None = None) -> dict[str, Any]:
        return self.auth.restart_browser(url=url)
