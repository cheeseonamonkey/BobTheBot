from __future__ import annotations

from ._base import ToolGroup, Tool, register, schema


@register
class EngineTools(ToolGroup):
    def tools(self) -> list[Tool]:
        task_names = self.app.task_names()
        task_enum = {"task": {"type": "string", "enum": task_names}}
        return [
            Tool("bob_engine_start",
                 "Start the bot engine loop.",
                 schema(),
                 lambda args: self.app.engine_start()),
            Tool("bob_engine_stop",
                 "Stop the bot engine loop.",
                 schema(),
                 lambda args: self.app.engine_stop()),
            Tool("bob_engine_pause",
                 "Pause task execution without stopping the engine thread.",
                 schema(),
                 lambda args: self.app.engine_pause()),
            Tool("bob_engine_resume",
                 "Resume a paused engine thread.",
                 schema(),
                 lambda args: self.app.engine_resume()),
            Tool("bob_task_list",
                 "List available bot tasks and their configurable parameters.",
                 schema(),
                 lambda args: {"tasks": self.app.list_tasks()}),
            Tool("bob_task_schema",
                 "Return the config schema for a task.",
                 schema(task_enum, ["task"]),
                 lambda args: {"task": str(args["task"]), "schema": self.app.task_schema(str(args["task"]))}),
            Tool("bob_set_task",
                 "Set active task. Optional fields configure task behavior.",
                 self._set_task_schema(),
                 lambda args: self.app.set_task(
                     str(args["task"]), **{k: v for k, v in args.items() if k != "task"}
                 )),
        ]

    def _set_task_schema(self) -> dict:
        task_names = self.app.task_names()
        props: dict = {"task": {"type": "string", "enum": task_names}}
        for name in task_names:
            for key, val in self.app.task_schema(name).get("properties", {}).items():
                if key not in props:
                    props[key] = val
        return {"type": "object", "properties": props, "required": ["task"], "additionalProperties": True}
