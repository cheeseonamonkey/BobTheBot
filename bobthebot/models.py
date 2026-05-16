# Backward-compat shim — canonical source is bobthebot.core.models
from .core.models import (
    ActionResult, EntityRef, InventoryItem, InventoryState, Observation,
    PlayerState, RuntimeStatus, ScreenPoint, SkillState, SkillsState,
    compact_dict, safe_int, validate_json_object, validate_json_value,
)
