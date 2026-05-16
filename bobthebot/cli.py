from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
import time
import zlib
from pathlib import Path
from typing import Any

from .app import BotApp
from .mcp_server import BobMcpServer

COMMANDS = (
    "status",
    "start",
    "stop",
    "backends",
    "tasks",
    "tools",
    "tool",
    "doctor",
    "demo-view",
    "auth-status",
    "auth-view",
    "observe",
    "script",
    "view",
)

ALIASES = {"run": "start", "quit": "stop", "backend": "backends", "task": "tasks", "check": "doctor", "demo": "demo-view", "auth": "auth-status", "see": "observe"}

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bobthebot-run",
        description="Run and inspect BobTheBot without memorizing MCP tool names.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Most useful commands:
  bobthebot-run check                 check paths and installed programs
  bobthebot-run see                   look at current bot/game state
  bobthebot-run run                   start Xvfb + RuneLite
  bobthebot-run quit                  stop managed processes
  bobthebot-run task                  list tasks
  bobthebot-run task mining           set task to mining
  bobthebot-run auth status           check browser login state
  bobthebot-run auth view             screenshot the auth browser
  bobthebot-run tools                 list raw MCP tools

Raw MCP escape hatch:
  bobthebot-run tool bob_status
  bobthebot-run tool bob_set_task task=mining
""",
    )
    parser.add_argument("command", nargs="?", metavar="COMMAND", help="Try: check, see, run, quit, task, auth, tools.")
    parser.add_argument("target", nargs="?", help="Thing to act on. Examples: task name, auth action, tool name, image path.")
    parser.add_argument("kv_args", nargs="*", metavar="KEY=VALUE", help="Optional settings, like target_name=rock or email=a@b.test.")
    parser.add_argument("-b", "--backend", default="null", choices=["null", "x11-cv"], help="Runtime backend. Default: null.")
    parser.add_argument("--args", default="{}", help="JSON object arguments for raw 'tool' calls.")
    parser.add_argument("-p", "--profile", default="default", help="Auth profile name. Default: default.")
    parser.add_argument("-r", "--renderer", default="auto", choices=["auto", "chafa", "none"], help="Image renderer. Default: auto.")
    parser.add_argument("--no-render", action="store_true", help="Do not draw screenshots in the terminal.")
    parser.add_argument("--view-size", default="100x40", metavar="WIDTHxHEIGHT", help="Terminal image size. Default: 100x40.")
    parser.add_argument("--watch", type=float, metavar="SECONDS", help="Repeat 'see'/'observe' every N seconds.")
    parser.add_argument("--live", nargs="?", const=2.0, type=float, metavar="SECONDS", help="Same as --watch, defaulting to 2 seconds.")
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    # Resolve aliases to canonical command
    if args.command in ALIASES:
        args.command = ALIASES[args.command]
    if args.command not in COMMANDS:
        parser.error(f"unknown command: {args.command}. Try 'bobthebot-run -h'.")
    if args.no_render:
        args.renderer = "none"
    if args.live is not None:
        args.watch = args.live

    app = BotApp(backend_name=args.backend)
    result = run_command(app, args, parser)

    if args.command != "script":
        maybe_render(result, args.renderer, args.view_size)
        sys.stderr.flush()
        print(json.dumps(result, indent=2))
        if isinstance(result, dict) and (result.get("error") or result.get("ok") is False):
            sys.exit(1)


def run_command(app: BotApp, args: argparse.Namespace, parser: argparse.ArgumentParser) -> dict[str, Any]:
    if args.command == "start":
        return app.start_runtime()
    if args.command == "stop":
        return app.stop_runtime()
    if args.command == "backends":
        return app.list_backends()
    if args.command == "tasks":
        return {"tasks": app.list_tasks()}
    if args.command == "tools":
        return list_tools(app)
    if args.command == "tool":
        return call_tool(app, args, parser)
    if args.command == "doctor":
        return doctor(app)
    if args.command == "demo-view":
        return demo_view(app)
    if args.command == "auth-status":
        return app.auth_status(args.profile)
    if args.command == "auth-view":
        return app.auth_screenshot(args.profile)
    if args.command == "observe":
        while True:
            result = app.observe()
            if args.watch:
                maybe_render(result, args.renderer, args.view_size)
                print(json.dumps(result, indent=2))
                time.sleep(args.watch)
                print("\033[2J\033[H", end="", flush=True)
            else:
                return result
    if args.command == "script":
        return run_script(app, args, parser)
    if args.command == "view":
        if not args.target:
            parser.error("file path is required for 'view'")
        return {"path": args.target}
    return app.status()


def list_tools(app: BotApp) -> dict[str, Any]:
    server = BobMcpServer(app)
    return {
        "tools": [
            {"name": tool.name, "description": tool.description}
            for tool in server.tools.values()
        ]
    }


def doctor(app: BotApp) -> dict[str, Any]:
    config = app.config
    browser = app.processes.find_browser()
    checks = {
        "browser": bool(browser),
        "runtime_dir": config.runtime_dir.exists(),
        "credentials_file": config.auth_credentials_file.exists(),
    }
    return {
        "ok": all(value for key, value in checks.items() if key != "credentials_file"),
        "checks": checks,
        "paths": {
            "root": str(config.root),
            "runtime": str(config.runtime_dir),
            "logs": str(config.logs_dir),
            "auth_credentials": str(config.auth_credentials_file),
        },
        "executables": {
            "browser": browser,
            "chafa": shutil.which("chafa"),
            "xvfb": shutil.which("Xvfb"),
            "java": shutil.which("java"),
        },
        "processes": app.processes.status(),
        "next": [
            "bobthebot-run demo-view",
            "bobthebot-run tools",
            "bobthebot-run tool bob_status",
            "bobthebot-run auth-status --renderer none",
        ],
    }


def demo_view(app: BotApp) -> dict[str, Any]:
    path = write_demo_png(app.config.logs_dir / "demo-view.png")
    return {
        "ok": True,
        "path": str(path),
        "message": "Generated deterministic demo image; chafa should render this in-terminal.",
    }


def write_demo_png(path: Path, width: int = 96, height: int = 48) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            band = 42 if ((x // 8) + (y // 4)) % 2 else 0
            row += bytes([
                min(255, 40 + x * 2 + band),
                min(255, 80 + y * 3 + band),
                min(255, 180 + ((x + y) % 32) * 2),
            ])
        rows.append(b"\x00" + bytes(row))

    def chunk(tag: bytes, data: bytes) -> bytes:
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(rows)))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)
    return path


def parse_tool_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> dict[str, Any]:
    if args.args != "{}" and args.kv_args:
        parser.error("use either --args JSON or key=value arguments, not both")
    if args.args != "{}":
        parsed = json.loads(args.args)
        if not isinstance(parsed, dict):
            parser.error("arguments must decode to a JSON object")
        return parsed
    tool_args: dict[str, Any] = {}
    for kv in args.kv_args:
        if "=" not in kv:
            parser.error(f"Invalid key=value pair: {kv}")
        key, value = kv.split("=", 1)
        try:
            tool_args[key] = json.loads(value)
        except json.JSONDecodeError:
            tool_args[key] = value
    return tool_args


def unwrap_tool_response(response: dict[str, Any]) -> dict[str, Any]:
    content = response.get("result", {}).get("content", [])
    if content and isinstance(content[0], dict) and content[0].get("type") == "text":
        try:
            payload = json.loads(content[0]["text"])
            return payload if isinstance(payload, dict) else {"value": payload}
        except (json.JSONDecodeError, TypeError):
            pass
    return response


def call_mcp_tool(app: BotApp, tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
    response = BobMcpServer(app).handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": tool_args},
        }
    )
    if response is None:
        return {"ok": False, "error": "MCP call produced no response"}
    return unwrap_tool_response(response)

def call_tool(app: BotApp, args: argparse.Namespace, parser: argparse.ArgumentParser) -> dict[str, Any]:
    tool_name = args.target
    if not tool_name:
        parser.error("tool name is required; run 'bobthebot-run tools' to inspect available tools")
    return call_mcp_tool(app, tool_name, parse_tool_args(args, parser))


def run_script(app: BotApp, args: argparse.Namespace, parser: argparse.ArgumentParser) -> dict:
    if not args.target:
        parser.error("script path is required")
    path = Path(args.target)
    if not path.exists():
        print(f"Script not found: {path}", file=sys.stderr)
        return {"ok": False, "error": "file not found"}

    with open(path) as f:
        code = f.read()

    ctx = {"app": app, "BotApp": BotApp, "render": lambda p: render_image(Path(p), args.renderer, args.view_size)}
    exec(code, ctx)
    return {"ok": True}


def iter_render_payloads(result: dict[str, Any]):
    yield result
    content = result.get("result", {}).get("content", []) if isinstance(result.get("result"), dict) else []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            try:
                inner = json.loads(item["text"])
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(inner, dict):
                yield inner
    data = result.get("data")
    if isinstance(data, dict):
        yield data


def is_image_path(value: Any) -> bool:
    return isinstance(value, str) and value.lower().endswith((".png", ".jpg", ".jpeg", ".ppm"))

def maybe_render(result: Any, renderer: str, size: str) -> None:
    if renderer == "none" or not isinstance(result, dict):
        return
    for nested in iter_render_payloads(result):
        for key in ("screenshot", "path", "file"):
            value = nested.get(key)
            if isinstance(value, str) and is_image_path(value):
                render_image(Path(value), renderer, size)
                return


def render_image(path: Path, renderer: str = "auto", size: str = "100x40") -> bool:
    if renderer == "none":
        return False
    executable = shutil.which("chafa") if renderer in ("auto", "chafa") else None
    if not executable:
        return False
    subprocess.run([executable, "--symbols", "block", "--size", size, str(path)], check=False, stdout=sys.stderr)
    return True


if __name__ == "__main__":
    main()
