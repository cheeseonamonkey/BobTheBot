from __future__ import annotations

from ._base import ToolGroup, Tool, register, schema

_backend_schema_props = {"backend": {"type": "string"}}


@register
class RuntimeTools(ToolGroup):
    def tools(self) -> list[Tool]:
        backend_names = self.app.backend_names()
        backend_enum = {"backend": {"type": "string", "enum": backend_names}}
        return [
            Tool("bob_status",
                 "Return process, engine, task, and backend status.",
                 schema(),
                 lambda args: self.app.status()),
            Tool("bob_backend_list",
                 "List available runtime backends and their capabilities.",
                 schema(),
                 lambda args: self.app.list_backends()),
            Tool("bob_runtime_status",
                 "Return selected runtime backend status only.",
                 schema(),
                 lambda args: self.app.backend_status()),
            Tool("bob_start_runtime",
                 "Start Xvfb and RuneLite.",
                 schema(),
                 lambda args: self.app.start_runtime()),
            Tool("bob_stop_runtime",
                 "Stop managed runtime processes and bot engine.",
                 schema(),
                 lambda args: self.app.stop_runtime()),
            Tool("bob_set_backend",
                 "Select backend: null, x11-cv, or dreambot.",
                 schema(backend_enum, ["backend"]),
                 lambda args: self.app.set_backend(str(args["backend"]))),
        ]
