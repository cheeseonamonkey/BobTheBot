from __future__ import annotations

from ..core.models import EntityRef
from ._base import ToolGroup, Tool, register, schema

_entity = {
    "kind": {"type": "string", "enum": ["npc", "object", "grounditem"]},
    "name": {"type": "string"},
    "action": {"type": "string"},
    "radius": {"type": "integer", "default": 15, "minimum": 1, "maximum": 100},
}
_click = {
    "x": {"type": "integer", "minimum": 0},
    "y": {"type": "integer", "minimum": 0},
    "button": {"type": "integer", "default": 1, "enum": [1, 2, 3]},
}


@register
class InputTools(ToolGroup):
    def tools(self) -> list[Tool]:
        return [
            Tool("bob_interact",
                 "Interact with a semantic target through the selected backend.",
                 schema(_entity, ["kind"]),
                 self._interact),
            Tool("bob_click",
                 "Click screen coordinates through the selected backend.",
                 schema(_click, ["x", "y"]),
                 lambda args: self.app.click(int(args["x"]), int(args["y"]), int(args.get("button", 1)))),
            Tool("bob_type_text",
                 "Type text through the selected backend.",
                 schema({"text": {"type": "string", "minLength": 1}}, ["text"]),
                 lambda args: self.app.type_text(str(args["text"]))),
            Tool("bob_press_key",
                 "Press a key through the selected backend.",
                 schema({"key": {"type": "string", "minLength": 1}}, ["key"]),
                 lambda args: self.app.press_key(str(args["key"]))),
        ]

    def _interact(self, args: dict) -> dict:
        self.app.require_capability("semantic_interact")
        target = EntityRef(
            kind=str(args["kind"]),
            name=str(args.get("name", "")),
            action=str(args.get("action", "")),
            radius=int(args.get("radius", 15)),
        )
        return self.app.interact(target)
