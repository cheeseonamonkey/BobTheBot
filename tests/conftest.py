from __future__ import annotations

import json
from typing import Any

from bobthebot.core.models import (
    ActionResult,
    InventoryState,
    Observation,
    RuntimeStatus,
    SkillsState,
)


class FakeResponseCtx:
    """Context-manager fake for urllib.request.urlopen responses."""

    def __init__(self, body: bytes):
        self._body = body

    @classmethod
    def json(cls, payload: Any) -> "FakeResponseCtx":
        return cls(json.dumps(payload).encode())

    def __enter__(self) -> "FakeResponseCtx":
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def read(self) -> bytes:
        return self._body


class FakeBackend:
    """Reusable BotBackend test double.

    Records every call in self.calls as (method_name, *args).
    Configurable capabilities and interact_result for testing
    capability-gating and task logic without a real backend.
    """

    name = "fake"
    capabilities: tuple[str, ...] = (
        "observe",
        "semantic_interact",
        "raw_input",
        "player",
        "inventory",
        "skills",
        "nearby_entities",
    )

    def __init__(
        self,
        capabilities: tuple[str, ...] | None = None,
        interact_result: ActionResult | None = None,
    ) -> None:
        if capabilities is not None:
            self.capabilities = capabilities
        self.interact_result = interact_result or ActionResult(True, "interact")
        self.calls: list[tuple] = []

    def status(self) -> RuntimeStatus:
        return RuntimeStatus(backend=self.name, ready=True)

    def observe(self) -> Observation:
        self.calls.append(("observe",))
        return Observation(source=self.name, data={})

    def click(self, x: int, y: int, button: int = 1) -> ActionResult:
        self.calls.append(("click", x, y, button))
        return ActionResult(True, "click")

    def type_text(self, text: str) -> ActionResult:
        self.calls.append(("type_text", text))
        return ActionResult(True, "type_text")

    def press_key(self, key: str) -> ActionResult:
        self.calls.append(("press_key", key))
        return ActionResult(True, "press_key")

    def interact(self, target: Any) -> ActionResult:
        self.calls.append(("interact", target))
        return ActionResult(
            self.interact_result.ok,
            "interact",
            target=target.name if hasattr(target, "name") else str(target),
            error=self.interact_result.error,
        )

    def player(self) -> dict[str, Any]:
        self.calls.append(("player",))
        return {}

    def inventory(self) -> InventoryState:
        self.calls.append(("inventory",))
        return InventoryState()

    def skills(self) -> SkillsState:
        self.calls.append(("skills",))
        return SkillsState()

    def nearby(self, kind: str, name: str = "", radius: int = 15) -> dict[str, Any]:
        self.calls.append(("nearby", kind, name, radius))
        return {f"{kind}s": []}
