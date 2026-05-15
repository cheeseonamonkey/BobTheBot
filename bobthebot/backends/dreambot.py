from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from ..models import (
    ActionResult,
    EntityRef,
    InventoryState,
    Observation,
    PlayerState,
    RuntimeStatus,
    SkillsState,
)


class DreamBotBridgeBackend:
    name = "dreambot-bridge"
    capabilities = ("observe", "player", "inventory", "skills", "nearby_entities", "semantic_interact", "chat")

    def __init__(self, base_url: str = "http://127.0.0.1:19132", timeout: float = 3.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(self, path: str, **params: Any) -> dict[str, Any]:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"
        with urllib.request.urlopen(url, timeout=self.timeout) as response:
            return json.loads(response.read())

    def status(self) -> RuntimeStatus:
        try:
            data = self.request("/api/status")
            data["capabilities"] = self.capabilities
            return RuntimeStatus(backend=self.name, ready=not bool(data.get("error")), detail=data)
        except OSError as exc:
            return RuntimeStatus(backend=self.name, ready=False, error=str(exc))

    def observe(self) -> Observation:
        data = {
            "status": self.status().to_dict(),
            "player": self.player(),
            "inventory": self.inventory(),
            "skills": self.skills(),
        }
        return Observation(source=self.name, data=data)

    def player(self) -> PlayerState | dict[str, Any]:
        data = self._safe("/api/player")
        if "error" in data:
            return data
        return PlayerState.from_dreambot(data)

    def inventory(self) -> InventoryState | dict[str, Any]:
        data = self._safe("/api/inventory")
        if "error" in data:
            return data
        return InventoryState.from_dreambot(data)

    def skills(self) -> SkillsState | dict[str, Any]:
        data = self._safe("/api/skills")
        if "error" in data:
            return data
        return SkillsState.from_dreambot(data)

    def nearby(self, kind: str, name: str = "", radius: int = 15) -> dict[str, Any]:
        paths = {
            "npc": "/api/npcs",
            "object": "/api/objects",
            "grounditem": "/api/grounditems",
        }
        if kind not in paths:
            return {"error": f"Unsupported nearby kind: {kind}"}
        return self.request(paths[kind], name=name, radius=radius)

    def interact(self, target: EntityRef) -> ActionResult:
        data = self.request(
            "/api/interact",
            type=target.kind,
            name=target.name,
            action=target.action,
            radius=target.radius,
        )
        return ActionResult(bool(data.get("ok")), "interact", target=data.get("target") or target.name, data=data)

    def click(self, x: int, y: int, button: int = 1) -> ActionResult:
        return ActionResult(False, "click", error="DreamBot bridge does not expose raw screen clicks")

    def type_text(self, text: str) -> ActionResult:
        data = self.request("/api/chat", text=text)
        return ActionResult(bool(data.get("ok")), "type_text", data=data)

    def press_key(self, key: str) -> ActionResult:
        return ActionResult(False, "press_key", target=key, error="DreamBot bridge does not expose raw key presses")

    def _safe(self, path: str) -> dict[str, Any]:
        try:
            return self.request(path)
        except OSError as exc:
            return {"error": str(exc)}
