from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from .models import EntityRef, validate_json_object

if TYPE_CHECKING:
    from .engine import BotEngine


@dataclass
class Task:
    name: str = "idle"
    status: str = "idle"
    started_at: float | None = None
    required_capabilities: tuple[str, ...] = ()

    def on_start(self, engine: BotEngine) -> None:
        self.status = "running"
        self.started_at = time.time()

    def execute(self, engine: BotEngine) -> bool:
        return True

    def on_stop(self, engine: BotEngine) -> None:
        self.status = "stopped"

    @classmethod
    def describe(cls) -> dict[str, object]:
        return {"name": "task", "description": "Base task."}

    @classmethod
    def input_schema(cls) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "additionalProperties": False}


class IdleTask(Task):
    def __init__(self):
        super().__init__(name="idle")

    @classmethod
    def describe(cls) -> dict[str, object]:
        return {
            "name": "idle",
            "description": "Do nothing while keeping the engine alive.",
            "required_capabilities": [],
            "input_schema": cls.input_schema(),
        }


@dataclass
class MiningTask(Task):
    target_name: str = "rock"
    action: str = "Mine"
    radius: int = 15
    last_action_at: float = field(default=0.0)
    cooldown: float = 5.0

    def __post_init__(self) -> None:
        self.name = "mining"
        self.required_capabilities = ("semantic_interact",)

    def execute(self, engine: BotEngine) -> bool:
        now = time.time()
        if now - self.last_action_at < self.cooldown:
            return True
        result = engine.backend.interact(
            EntityRef(kind="object", name=self.target_name, action=self.action, radius=self.radius)
        )
        engine.last_result = result.to_dict()
        if result.ok:
            self.last_action_at = now
        return True

    @classmethod
    def describe(cls) -> dict[str, object]:
        return {
            "name": "mining",
            "description": "Repeatedly interacts with a nearby mineable object through semantic runtime APIs.",
            "input_schema": cls.input_schema(),
            "required_capabilities": ["semantic_interact"],
        }

    @classmethod
    def input_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target_name": {
                    "type": "string",
                    "default": "rock",
                    "minLength": 1,
                    "description": "Object name substring to mine.",
                },
                "action": {
                    "type": "string",
                    "default": "Mine",
                    "minLength": 1,
                    "description": "Interaction action.",
                },
                "radius": {
                    "type": "integer",
                    "default": 15,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Search radius in tiles for semantic backends.",
                },
                "cooldown": {
                    "type": "number",
                    "default": 5.0,
                    "minimum": 0.0,
                    "maximum": 300.0,
                    "description": "Minimum seconds between interaction attempts.",
                },
            },
            "additionalProperties": False,
        }


@dataclass
class InteractTask(Task):
    kind: str = "npc"
    target_name: str = ""
    action: str = ""
    radius: int = 15
    last_action_at: float = field(default=0.0)
    cooldown: float = 5.0

    def __post_init__(self) -> None:
        self.name = "interact"
        self.required_capabilities = ("semantic_interact",)

    def execute(self, engine: BotEngine) -> bool:
        now = time.time()
        if now - self.last_action_at < self.cooldown:
            return True
        result = engine.backend.interact(
            EntityRef(kind=self.kind, name=self.target_name, action=self.action, radius=self.radius)
        )
        engine.last_result = result.to_dict()
        if result.ok:
            self.last_action_at = now
        return True

    @classmethod
    def describe(cls) -> dict[str, object]:
        return {
            "name": "interact",
            "description": "Repeatedly interacts with a nearby entity (NPC, Object, GroundItem) through semantic runtime APIs.",
            "input_schema": cls.input_schema(),
            "required_capabilities": ["semantic_interact"],
        }

    @classmethod
    def input_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["npc", "object", "grounditem"],
                    "default": "npc",
                    "description": "Entity kind.",
                },
                "target_name": {
                    "type": "string",
                    "default": "",
                    "description": "Entity name substring.",
                },
                "action": {
                    "type": "string",
                    "default": "",
                    "description": "Interaction action.",
                },
                "radius": {
                    "type": "integer",
                    "default": 15,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Search radius in tiles.",
                },
                "cooldown": {
                    "type": "number",
                    "default": 5.0,
                    "minimum": 0.0,
                    "maximum": 300.0,
                    "description": "Minimum seconds between attempts.",
                },
            },
            "additionalProperties": False,
        }

@dataclass(frozen=True)
class TaskSpec:
    name: str
    task_type: type[Task]

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.task_type.input_schema()

    def describe(self) -> dict[str, object]:
        return self.task_type.describe()

    def create(self, config: dict[str, Any] | None = None) -> Task:
        values = dict(config or {})
        validate_task_config(self.name, self.input_schema, values)
        return self.task_type(**values)


class TaskRegistry:
    def __init__(self):
        self._items: dict[str, TaskSpec] = {}

    def register(self, name: str, task_type: type[Task]) -> None:
        self._items[name] = TaskSpec(name=name, task_type=task_type)

    def names(self) -> list[str]:
        return sorted(self._items)

    def describe(self) -> list[dict[str, object]]:
        return [self._items[name].describe() for name in self.names()]

    def schema_for(self, name: str) -> dict[str, Any]:
        return self._get(name).input_schema

    def create(self, name: str, config: dict[str, Any] | None = None) -> Task:
        return self._get(name).create(config)

    def _get(self, name: str) -> TaskSpec:
        if name not in self._items:
            raise ValueError(f"Unknown task: {name}")
        return self._items[name]


def default_task_registry() -> TaskRegistry:
    registry = TaskRegistry()
    registry.register("idle", IdleTask)
    registry.register("mining", MiningTask)
    registry.register("interact", InteractTask)
    return registry


def validate_task_config(task_name: str, schema: dict[str, Any], values: dict[str, Any]) -> None:
    try:
        validate_json_object(schema, values, f"Task {task_name}")
    except ValueError as exc:
        raise ValueError(str(exc).replace("unexpected argument", "unexpected config key")) from exc
