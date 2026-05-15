from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or isinstance(value, bool):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def validate_json_object(schema: dict[str, Any], values: dict[str, Any], label: str) -> None:
    properties = schema.get("properties", {})
    for key in schema.get("required", []):
        if key not in values:
            raise ValueError(f"{label}: missing required argument: {key}")
    if schema.get("additionalProperties") is False:
        extra = sorted(set(values) - set(properties))
        if extra:
            raise ValueError(f"{label}: unexpected argument(s): {', '.join(extra)}")
    for key, value in values.items():
        if key in properties:
            validate_json_value(label, key, value, properties[key])


def validate_json_value(label: str, key: str, value: Any, prop: dict[str, Any]) -> None:
    expected = prop.get("type")
    validators = {
        "string": _validate_string,
        "integer": _validate_integer,
        "number": _validate_number,
        "boolean": _validate_boolean,
    }
    if expected in validators:
        validators[expected](label, key, value, prop)
    if "enum" in prop and value not in prop["enum"]:
        raise ValueError(f"{label}: {key} must be one of {prop['enum']}")
    if isinstance(value, int | float) and not isinstance(value, bool):
        _validate_numeric_bounds(label, key, value, prop)


def _validate_string(label: str, key: str, value: Any, prop: dict[str, Any]) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{label}: {key} must be a string")
    if len(value) < int(prop.get("minLength", 0)):
        raise ValueError(f"{label}: {key} must not be empty")


def _validate_integer(label: str, key: str, value: Any, prop: dict[str, Any]) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label}: {key} must be an integer")


def _validate_number(label: str, key: str, value: Any, prop: dict[str, Any]) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{label}: {key} must be a number")
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"{label}: {key} must be finite")


def _validate_boolean(label: str, key: str, value: Any, prop: dict[str, Any]) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"{label}: {key} must be a boolean")


def _validate_numeric_bounds(label: str, key: str, value: int | float, prop: dict[str, Any]) -> None:
    if "minimum" in prop and value < prop["minimum"]:
        raise ValueError(f"{label}: {key} must be >= {prop['minimum']}")
    if "maximum" in prop and value > prop["maximum"]:
        raise ValueError(f"{label}: {key} must be <= {prop['maximum']}")


def compact_dict(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [compact_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: compact_dict(item) for key, item in value.items() if item is not None}
    return value


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    action: str
    target: str | None = None
    error: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return compact_dict(asdict(self))


@dataclass(frozen=True)
class RuntimeStatus:
    backend: str
    ready: bool
    detail: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return compact_dict(asdict(self))


@dataclass(frozen=True)
class ScreenPoint:
    x: int
    y: int

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True)
class EntityRef:
    kind: str
    name: str = ""
    action: str = ""
    radius: int = 15
    entity_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return compact_dict(asdict(self))


@dataclass(frozen=True)
class Observation:
    source: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "data": compact_dict(self.data)}


@dataclass(frozen=True)
class PlayerState:
    name: str | None = None
    tile: dict[str, int] | None = None
    health: int | None = None
    animation: int | None = None
    is_moving: bool | None = None
    is_animating: bool | None = None

    @classmethod
    def from_dreambot(cls, data: dict[str, Any]) -> PlayerState:
        return cls(
            name=data.get("name"),
            tile=data.get("tile"),
            health=data.get("health"),
            animation=data.get("animation"),
            is_moving=data.get("isMoving"),
            is_animating=data.get("isAnimating"),
        )

    def to_dict(self) -> dict[str, Any]:
        return compact_dict(asdict(self))


@dataclass(frozen=True)
class InventoryItem:
    name: str
    item_id: int
    amount: int = 1
    slot: int | None = None

    @classmethod
    def from_dreambot(cls, data: dict[str, Any]) -> InventoryItem:
        return cls(
            name=str(data.get("name", "")),
            item_id=safe_int(data.get("id"), -1),
            amount=safe_int(data.get("amount"), 1),
            slot=None if data.get("slot") is None else safe_int(data.get("slot"), -1),
        )

    def to_dict(self) -> dict[str, Any]:
        return compact_dict(asdict(self))


@dataclass(frozen=True)
class InventoryState:
    items: list[InventoryItem] = field(default_factory=list)

    @classmethod
    def from_dreambot(cls, data: dict[str, Any]) -> InventoryState:
        return cls(items=[InventoryItem.from_dreambot(item) for item in data.get("items", [])])

    @property
    def count(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict[str, Any]:
        return {"count": self.count, "items": [item.to_dict() for item in self.items]}


@dataclass(frozen=True)
class SkillState:
    name: str
    level: int
    xp: int
    boosted: int | None = None

    @classmethod
    def from_dreambot(cls, name: str, data: dict[str, Any]) -> SkillState:
        return cls(
            name=name,
            level=safe_int(data.get("level"), 0),
            xp=safe_int(data.get("xp"), 0),
            boosted=None if data.get("boosted") is None else safe_int(data.get("boosted"), 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return compact_dict(asdict(self))


@dataclass(frozen=True)
class SkillsState:
    skills: dict[str, SkillState] = field(default_factory=dict)

    @classmethod
    def from_dreambot(cls, data: dict[str, Any]) -> SkillsState:
        return cls(
            skills={
                name: SkillState.from_dreambot(name, value)
                for name, value in data.items()
                if isinstance(value, dict)
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {name: skill.to_dict() for name, skill in self.skills.items()}
