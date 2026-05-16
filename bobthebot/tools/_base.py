from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..app import BotApp

Json = dict[str, Any]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: Json
    handler: Callable[[Json], Any]

    def as_mcp(self) -> Json:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


def schema(properties: Json | None = None, required: list[str] | None = None) -> Json:
    result: Json = {"type": "object", "properties": properties or {}, "additionalProperties": False}
    if required:
        result["required"] = required
    return result


class ToolGroup(ABC):
    """Base class for a self-contained group of MCP tools.

    Subclass, decorate with @register, implement tools().
    Handlers receive raw JSON args and must return a JSON-serialisable dict.
    They should call self.app.* only — never app._engine, app.processes, etc.
    """

    def __init__(self, app: BotApp) -> None:
        self.app = app

    @abstractmethod
    def tools(self) -> list[Tool]:
        raise NotImplementedError


class ToolRegistry:
    def __init__(self) -> None:
        self._groups: list[type[ToolGroup]] = []

    def register(self, cls: type[ToolGroup]) -> type[ToolGroup]:
        """Decorator: @register on any ToolGroup subclass."""
        self._groups.append(cls)
        return cls

    def build(self, app: BotApp) -> dict[str, Tool]:
        return {
            tool.name: tool
            for cls in self._groups
            for tool in cls(app).tools()
        }


_registry = ToolRegistry()
register = _registry.register
build_tools = _registry.build
