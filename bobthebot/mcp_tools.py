from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


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


def build_tools(server: Any) -> dict[str, Tool]:
    task_names = server.app.engine.task_registry.names() if hasattr(server, "app") and hasattr(server.app, "engine") else ["idle", "mining"]

    backend_schema = {"backend": {"type": "string", "enum": ["null", "x11-cv", "dreambot"]}}
    task_schema = {
        "task": {"type": "string", "enum": task_names},
        "target_name": {"type": "string"},
        "action": {"type": "string"},
        "radius": {"type": "integer"},
        "cooldown": {"type": "number"},
    }
    entity_schema = {
        "kind": {"type": "string", "enum": ["npc", "object", "grounditem"]},
        "name": {"type": "string"},
        "action": {"type": "string"},
        "radius": {"type": "integer", "default": 15, "minimum": 1, "maximum": 100},
    }
    nearby_schema = {
        "kind": {"type": "string", "enum": ["npc", "object", "grounditem"]},
        "name": {"type": "string"},
        "radius": {"type": "integer", "default": 15, "minimum": 1, "maximum": 100},
    }
    profile_schema = {"profile": {"type": "string", "default": "default", "minLength": 1}}
    credential_schema = {
        "profile": {"type": "string", "default": "default", "minLength": 1},
        "email": {"type": "string", "minLength": 1},
        "password": {"type": "string", "minLength": 1},
    }
    auth_start_schema = {
        "profile": {"type": "string", "default": "default", "minLength": 1},
        "email": {"type": "string", "minLength": 1},
        "password": {"type": "string", "minLength": 1},
        "display_name": {"type": "string", "minLength": 1},
        "submit": {"type": "boolean", "default": True},
    }
    auth_continue_schema = {
        "profile": {"type": "string", "default": "default", "minLength": 1},
        "email_code": {"type": "string", "minLength": 1},
        "two_factor_code": {"type": "string", "minLength": 1},
    }
    def task_schema_generator() -> Json:
        base = schema(task_schema, ["task"])
        base["additionalProperties"] = True
        return base

    tools = [
        Tool("bob_status", "Return process, engine, task, and backend status.", schema(), lambda args: server.app.status()),
        Tool("bob_backend_list", "List available runtime backends and their capabilities.", schema(), lambda args: server.app.list_backends()),
        Tool("bob_runtime_status", "Return selected runtime backend status only.", schema(), lambda args: server.app.engine.backend.status().to_dict()),
        Tool("bob_start_runtime", "Start Xvfb and RuneLite.", schema(), server._start_runtime),
        Tool("bob_stop_runtime", "Stop managed runtime processes and bot engine.", schema(), server._stop_runtime),
        Tool("bob_set_backend", "Select backend: null, x11-cv, or dreambot.", schema(backend_schema, ["backend"]), server._set_backend),
        Tool("bob_backend_set", "Alias for bob_set_backend.", schema(backend_schema, ["backend"]), server._set_backend),
        Tool("bob_observe", "Observe current game/client state through the selected backend.", schema(), lambda args: server.app.engine.observe()),
        Tool("bob_player", "Return semantic player state when supported by the selected backend.", schema(), lambda args: server._with_capability("player", lambda: server._compact_backend_value(server.app.engine.backend.player()))),
        Tool("bob_inventory", "Return semantic inventory state when supported by the selected backend.", schema(), lambda args: server._with_capability("inventory", lambda: server._compact_backend_value(server.app.engine.backend.inventory()))),
        Tool("bob_skills", "Return semantic skill state when supported by the selected backend.", schema(), lambda args: server._with_capability("skills", lambda: server._compact_backend_value(server.app.engine.backend.skills()))),
        Tool("bob_nearby", "List nearby NPCs, objects, or ground items through a semantic backend.", schema(nearby_schema, ["kind"]), server._nearby),
        Tool("bob_task_list", "List available bot tasks and their configurable parameters.", schema(), lambda args: {"tasks": server.app.engine.tasks()}),
        Tool("bob_task_schema", "Return the config schema for a task.", schema({"task": {"type": "string", "enum": task_names}}, ["task"]), server._task_schema),
        Tool("bob_engine_start", "Start the bot engine loop.", schema(), server._engine_start),
        Tool("bob_engine_stop", "Stop the bot engine loop.", schema(), server._engine_stop),
        Tool("bob_engine_pause", "Pause task execution without stopping the engine thread.", schema(), server._engine_pause),
        Tool("bob_engine_resume", "Resume a paused engine thread.", schema(), server._engine_resume),
        Tool("bob_set_task", "Set active task. Optional fields configure task behavior.", task_schema_generator(), server._set_task),
        Tool("bob_task_set", "Alias for bob_set_task.", task_schema_generator(), server._set_task),
        Tool("bob_interact", "Interact with a semantic target through the selected backend.", schema(entity_schema, ["kind"]), server._interact),
        Tool("bob_click", "Click screen coordinates through the selected backend.", schema({"x": {"type": "integer", "minimum": 0}, "y": {"type": "integer", "minimum": 0}, "button": {"type": "integer", "default": 1, "enum": [1, 2, 3]}}, ["x", "y"]), server._click),
        Tool("bob_type_text", "Type text through the selected backend.", schema({"text": {"type": "string", "minLength": 1}}, ["text"]), server._type_text),
        Tool("bob_press_key", "Press a key through the selected backend.", schema({"key": {"type": "string", "minLength": 1}}, ["key"]), server._press_key),
        Tool("bob_auth_save_credentials", "Persist plaintext auth credentials for a profile.", schema(credential_schema, ["email", "password"]), server._auth_save_credentials),
        Tool("bob_auth_forget_credentials", "Forget saved auth credentials for a profile.", schema(profile_schema), server._auth_forget_credentials),
        Tool("bob_auth_status", "Return current browser auth status.", schema(profile_schema), server._auth_status),
        Tool("bob_auth_register_start", "Start or continue automated Jagex registration.", schema(auth_start_schema), server._auth_register_start),
        Tool("bob_auth_login_start", "Start or continue automated Jagex login.", schema(auth_start_schema), server._auth_login_start),
        Tool("bob_auth_continue", "Submit an email or two-factor code when requested.", schema(auth_continue_schema), server._auth_continue),
        Tool("bob_auth_screenshot", "Capture current auth browser screenshot.", schema(profile_schema), server._auth_screenshot),
        Tool("bob_auth_open", "Open an arbitrary auth/browser URL.", schema({"url": {"type": "string", "minLength": 1}}, ["url"]), server._auth_open),
        Tool("bob_auth_verification_check", "Check configured verification providers for a code.", schema({"profile": {"type": "string", "default": "default", "minLength": 1}, "purpose": {"type": "string", "default": "auth", "minLength": 1}}), server._auth_verification_check),
    ]
    return {tool.name: tool for tool in tools}
