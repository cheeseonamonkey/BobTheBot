from __future__ import annotations

from ._base import ToolGroup, Tool, register, schema

_profile = {"profile": {"type": "string", "default": "default", "minLength": 1}}
_nearby = {
    "kind": {"type": "string", "enum": ["npc", "object", "grounditem"]},
    "name": {"type": "string"},
    "radius": {"type": "integer", "default": 15, "minimum": 1, "maximum": 100},
}


@register
class ObservationTools(ToolGroup):
    def tools(self) -> list[Tool]:
        return [
            Tool("bob_observe",
                 "Observe current game/client state through the selected backend.",
                 schema(),
                 self._observe),
            Tool("bob_view",
                 "Capture and view auth browser screenshot.",
                 schema(_profile),
                 self._view),
            Tool("bob_player",
                 "Return semantic player state when supported by the selected backend.",
                 schema(),
                 self._player),
            Tool("bob_inventory",
                 "Return semantic inventory state when supported by the selected backend.",
                 schema(),
                 self._inventory),
            Tool("bob_skills",
                 "Return semantic skill state when supported by the selected backend.",
                 schema(),
                 self._skills),
            Tool("bob_nearby",
                 "List nearby NPCs, objects, or ground items through a semantic backend.",
                 schema(_nearby, ["kind"]),
                 self._nearby),
        ]

    def _observe(self, args: dict) -> dict:
        result = self.app.observe()
        path = result.get("screenshot") or result.get("path") or result.get("file")
        if path:
            result["__image_path__"] = path
        return result

    def _view(self, args: dict) -> dict:
        profile = str(args.get("profile", "default"))
        result = self.app.auth_screenshot(profile)
        path = result.get("path")
        if path:
            result["__image_path__"] = str(path)
        return result

    def _player(self, args: dict) -> dict:
        self.app.require_capability("player")
        return self.app.player()

    def _inventory(self, args: dict) -> dict:
        self.app.require_capability("inventory")
        return self.app.inventory()

    def _skills(self, args: dict) -> dict:
        self.app.require_capability("skills")
        return self.app.skills()

    def _nearby(self, args: dict) -> dict:
        self.app.require_capability("nearby_entities")
        return self.app.nearby(
            kind=str(args["kind"]),
            name=str(args.get("name", "")),
            radius=int(args.get("radius", 15)),
        )
