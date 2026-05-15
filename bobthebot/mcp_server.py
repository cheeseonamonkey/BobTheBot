from __future__ import annotations

import base64
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .app import BotApp
from .models import EntityRef, compact_dict, validate_json_object
from .mcp_tools import Tool, build_tools


Json = dict[str, Any]


class BobMcpServer:
    def __init__(self, app: BotApp | None = None):
        self.app = app or BotApp()
        self.tools = build_tools(self)

    def handle(self, message: Any) -> Json | None:
        if not isinstance(message, dict):
            return self._error({}, -32600, "Invalid Request: message must be an object")
        if "method" not in message:
            return self._error(message, -32600, "Invalid Request: method is required")
        method = message.get("method")
        if not isinstance(method, str):
            return self._error(message, -32600, "Invalid Request: method must be a string")
        if method.startswith("notifications/"):
            return None
        try:
            return self._result(message, self._handle_method(method, message))
        except NotImplementedError as exc:
            return self._error(message, -32601, str(exc))
        except ValueError as exc:
            return self._error(message, -32600, str(exc))
        except Exception as exc:
            return self._error(message, -32000, str(exc))

    def _handle_method(self, method: str, message: Json) -> Json:
        if method == "initialize":
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "bobthebot", "version": "0.1.0"},
            }
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [tool.as_mcp() for tool in self.tools.values()]}
        if method == "tools/call":
            name, arguments = self._tool_call_args(message)
            if arguments is None:
                return self._tool_error(f"{name}: arguments must be an object")
            return self._call_tool(name, arguments)
        raise NotImplementedError(f"Method not found: {method}")

    def _call_tool(self, name: str | None, arguments: Json) -> Json:
        if not isinstance(name, str) or not name:
            return self._tool_error("Tool name is required")
        if name not in self.tools:
            return self._tool_error(f"Unknown tool: {name}; call tools/list to inspect available tools")
        try:
            tool = self.tools[name]
            self._validate_arguments(tool, arguments)
            payload = compact_dict(tool.handler(arguments))
        except Exception as exc:
            return self._tool_error(str(exc))
        is_error = isinstance(payload, dict) and bool(payload.get("error"))
        return self._tool_response(payload, is_error)

    def _tool_response(self, payload: Any, is_error: bool = False) -> Json:
        try:
            image_path = None
            if isinstance(payload, dict):
                image_path = payload.pop("__image_path__", None)
            text = json.dumps(payload, allow_nan=False)
        except (TypeError, ValueError) as exc:
            fallback = {"error": f"Tool returned non-JSON-serializable payload: {exc}"}
            return {"content": [{"type": "text", "text": json.dumps(fallback)}], "isError": True}
        content = [{"type": "text", "text": text}]
        if image_path and Path(image_path).exists():
            try:
                data = base64.b64encode(Path(image_path).read_bytes()).decode()
                content.append({"type": "image", "data": data, "mimeType": "image/png"})
            except Exception:
                pass
        return {"content": content, "isError": is_error}

    def _tool_error(self, message: str) -> Json:
        return self._tool_response({"error": message}, True)

    def _start_runtime(self, args: Json) -> Json:
        return {
            "xvfb": self.app.processes.start_xvfb(),
            "runelite": self.app.processes.start_runelite(),
            "status": self.app.processes.status(),
        }

    def _stop_runtime(self, args: Json) -> Json:
        self.app.engine.stop()
        self.app.processes.stop_all()
        return {"ok": True}

    def _set_backend(self, args: Json) -> Json:
        return self.app.set_backend(str(args["backend"]))

    def _engine_start(self, args: Json) -> Json:
        self.app.engine.start()
        return self.app.engine.status()

    def _engine_stop(self, args: Json) -> Json:
        self.app.engine.stop()
        return self.app.engine.status()

    def _engine_pause(self, args: Json) -> Json:
        self.app.engine.pause()
        return self.app.engine.status()

    def _engine_resume(self, args: Json) -> Json:
        self.app.engine.resume()
        return self.app.engine.status()

    def _set_task(self, args: Json) -> Json:
        task = str(args["task"])
        kwargs = {k: v for k, v in args.items() if k != "task"}
        self.app.engine.set_task(task, **kwargs)
        return self.app.engine.status()

    def _task_schema(self, args: Json) -> Json:
        task = str(args["task"])
        return {"task": task, "schema": self.app.engine.task_schema(task)}

    def _interact(self, args: Json) -> Json:
        self._require_capability("semantic_interact")
        target = EntityRef(
            kind=str(args["kind"]),
            name=str(args.get("name", "")),
            action=str(args.get("action", "")),
            radius=int(args.get("radius", 15)),
        )
        return self.app.engine.backend.interact(target).to_dict()

    def _nearby(self, args: Json) -> Json:
        self._require_capability("nearby_entities")
        return self.app.engine.backend.nearby(
            kind=str(args["kind"]),
            name=str(args.get("name", "")),
            radius=int(args.get("radius", 15)),
        )

    def _with_capability(self, capability: str, action: Callable[[], Json]) -> Json:
        self._require_capability(capability)
        return action()

    def _player(self, args: Json) -> Json:
        self._require_capability("player")
        return compact_dict(self.app.engine.backend.player())

    def _inventory(self, args: Json) -> Json:
        self._require_capability("inventory")
        return compact_dict(self.app.engine.backend.inventory())

    def _skills(self, args: Json) -> Json:
        self._require_capability("skills")
        return compact_dict(self.app.engine.backend.skills())

    

    def _require_capability(self, capability: str) -> None:
        capabilities = set(getattr(self.app.engine.backend, "capabilities", ()))
        if capability not in capabilities:
            raise ValueError(
                f"Backend {self.app.engine.backend.name} does not support {capability}; "
                f"available capabilities: {sorted(capabilities)}"
            )

    def _click(self, args: Json) -> Json:
        return self.app.engine.backend.click(int(args["x"]), int(args["y"]), int(args.get("button", 1))).to_dict()

    def _type_text(self, args: Json) -> Json:
        return self.app.engine.backend.type_text(str(args["text"])).to_dict()

    def _press_key(self, args: Json) -> Json:
        return self.app.engine.backend.press_key(str(args["key"])).to_dict()

    def _auth_save_credentials(self, args: Json) -> Json:
        return self.app.auth.save_credentials(
            profile=str(args.get("profile", "default")),
            email=str(args["email"]),
            password=str(args["password"]),
        )

    def _auth_forget_credentials(self, args: Json) -> Json:
        return self.app.auth.forget_credentials(str(args.get("profile", "default")))

    def _auth_status(self, args: Json) -> Json:
        return self.app.auth.status(str(args.get("profile", "default")))

    def _auth_register_start(self, args: Json) -> Json:
        return self.app.auth.register_start(**self._auth_start_args(args))

    def _auth_login_start(self, args: Json) -> Json:
        return self.app.auth.login_start(**self._auth_start_args(args))

    def _auth_continue(self, args: Json) -> Json:
        return self.app.auth.continue_flow(
            profile=str(args.get("profile", "default")),
            email_code=args.get("email_code"),
            two_factor_code=args.get("two_factor_code"),
        )

    def _auth_screenshot(self, args: Json) -> Json:
        return self.app.auth.screenshot(str(args.get("profile", "default")))

    def _observe(self, args: Json) -> Json:
        result = self.app.engine.observe()
        path = result.get("screenshot") or result.get("path") or result.get("file")
        if path:
            result["__image_path__"] = path
        return result

    def _view(self, args: Json) -> Json:
        profile = str(args.get("profile", "default"))
        path = self.app.auth.screenshot(profile)
        return {"path": str(path), "__image_path__": str(path)}

    def _auth_open(self, args: Json) -> Json:
        return self.app.auth.open(str(args["url"]))

    def _auth_verification_check(self, args: Json) -> Json:
        return self.app.auth.verification_check(
            profile=str(args.get("profile", "default")),
            purpose=str(args.get("purpose", "auth")),
        )

    def _auth_start_args(self, args: Json) -> Json:
        return {
            key: value
            for key, value in {
                "profile": str(args.get("profile", "default")),
                "email": args.get("email"),
                "password": args.get("password"),
                "display_name": args.get("display_name"),
                "submit": args.get("submit", True),
            }.items()
            if value is not None
        }


    def _result(self, message: Json, result: Json) -> Json:
        return {"jsonrpc": "2.0", "id": message.get("id"), "result": result}

    def _parse_error(self, text: str) -> Json:
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": text}}

    def _tool_call_args(self, message: Json) -> tuple[str | None, Json | None]:
        params = message.get("params", {})
        if not isinstance(params, dict):
            raise ValueError("tools/call params must be an object")
        name = params.get("name")
        if not isinstance(name, str) or not name:
            return None, {}
        arguments = params.get("arguments", {})
        if arguments is None:
            return name, {}
        if not isinstance(arguments, dict):
            return name, None
        return name, arguments

    def _error(self, message: Json, code: int, text: str) -> Json:
        return {"jsonrpc": "2.0", "id": message.get("id"), "error": {"code": code, "message": text}}

    def _validate_arguments(self, tool: Tool, arguments: Json) -> None:
        validate_json_object(tool.input_schema, arguments, tool.name)

    def serve(self) -> None:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                response = self.handle(json.loads(line))
            except json.JSONDecodeError as exc:
                response = self._parse_error(f"Parse error: {exc.msg}")
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()


def main() -> None:
    BobMcpServer().serve()


if __name__ == "__main__":
    main()
