from __future__ import annotations

from typing import Any, Protocol

from ..core.models import ActionResult, EntityRef, InventoryState, Observation, PlayerState, RuntimeStatus, SkillsState


class BotBackend(Protocol):
    name: str
    capabilities: tuple[str, ...]

    def status(self) -> RuntimeStatus:
        ...

    def observe(self) -> Observation:
        ...

    def click(self, x: int, y: int, button: int = 1) -> ActionResult:
        ...

    def type_text(self, text: str) -> ActionResult:
        ...

    def press_key(self, key: str) -> ActionResult:
        ...

    def interact(self, target: EntityRef) -> ActionResult:
        ...

    def player(self) -> PlayerState | dict[str, Any]:
        ...

    def inventory(self) -> InventoryState | dict[str, Any]:
        ...

    def skills(self) -> SkillsState | dict[str, Any]:
        ...

    def nearby(self, kind: str, name: str = "", radius: int = 15) -> dict[str, Any]:
        ...


class NullBackend:
    name = "null"
    capabilities = ("observe",)

    def status(self) -> RuntimeStatus:
        return RuntimeStatus(backend=self.name, ready=True, detail={"capabilities": self.capabilities})

    def observe(self) -> Observation:
        return Observation(source=self.name, data={"message": "No game backend attached."})

    def click(self, x: int, y: int, button: int = 1) -> ActionResult:
        return ActionResult(False, "click", error="null backend cannot click", data={"x": x, "y": y, "button": button})

    def type_text(self, text: str) -> ActionResult:
        return ActionResult(False, "type_text", error="null backend cannot type", data={"text_len": len(text)})

    def press_key(self, key: str) -> ActionResult:
        return ActionResult(False, "press_key", target=key, error="null backend cannot press keys")

    def interact(self, target: EntityRef) -> ActionResult:
        return ActionResult(False, "interact", target=target.name, error="null backend cannot interact")

    def player(self) -> dict[str, Any]:
        return {"error": "null backend has no player state"}

    def inventory(self) -> InventoryState:
        return InventoryState()

    def skills(self) -> SkillsState:
        return SkillsState()

    def nearby(self, kind: str, name: str = "", radius: int = 15) -> dict[str, Any]:
        return {"error": "null backend cannot inspect nearby entities", "kind": kind}
