from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from typing import Any

from .app import BotApp
from .core.models import compact_dict, validate_json_object
from .tools import Tool, build_tools


Json = dict[str, Any]


class BobMcpServer:
    def __init__(self, app: BotApp | None = None):
        self.app = app or BotApp()
        self.tools = build_tools(self.app)

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
