from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..backends.base import BotBackend, NullBackend
from ..backends.cv import X11CvBackend
from ..backends.dreambot import DreamBotBridgeBackend
from ..config import BotConfig


BackendFactory = Callable[[BotConfig], BotBackend]


@dataclass(frozen=True)
class BackendSpec:
    name: str
    description: str
    capabilities: tuple[str, ...]
    factory: BackendFactory

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": list(self.capabilities),
        }


class BackendRegistry:
    def __init__(self):
        self._items: dict[str, BackendSpec] = {}

    def register(self, spec: BackendSpec) -> None:
        self._items[spec.name] = spec

    def names(self) -> list[str]:
        return sorted(self._items)

    def describe(self) -> list[dict[str, object]]:
        return [self._items[name].to_dict() for name in self.names()]

    def create(self, name: str, config: BotConfig) -> BotBackend:
        if name not in self._items:
            raise ValueError(f"Unknown backend: {name}")
        return self._items[name].factory(config)


def default_backend_registry() -> BackendRegistry:
    registry = BackendRegistry()
    registry.register(
        BackendSpec(
            name="null",
            description="Safe no-game backend for testing engine and MCP behavior.",
            capabilities=NullBackend.capabilities,
            factory=lambda config: NullBackend(),
        )
    )
    registry.register(
        BackendSpec(
            name="x11-cv",
            description="X11 screenshot and raw input backend for RuneLite/CV automation.",
            capabilities=X11CvBackend.capabilities,
            factory=lambda config: X11CvBackend(config),
        )
    )
    registry.register(
        BackendSpec(
            name="dreambot",
            description="Semantic OSRS backend using the local DreamBot HTTP bridge.",
            capabilities=DreamBotBridgeBackend.capabilities,
            factory=lambda config: DreamBotBridgeBackend(config.dreambot_url),
        )
    )
    return registry
