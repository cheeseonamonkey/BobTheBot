#!/usr/bin/env python3
import sys
import json
import time
import subprocess
import asyncio
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).resolve().parent / "src"))

from config import *
from launcher import OSBCLauncher
from osbc import ENGINE
from tasks import IdleTask, MiningTask
from auth import OSBCAuth

LAUNCHER = OSBCLauncher()
AUTH = OSBCAuth()
TASK_MAP = {
    "idle": IdleTask,
    "mining": MiningTask
}

def tool(name, description, input_schema=None):
    return {"name": name, "description": description, "inputSchema": input_schema or {"type": "object", "properties": {}}}

TOOLS = [
    tool("osbc_start_all", "Start Xvfb and RuneLite"),
    tool("osbc_stop_all", "Stop all OSBC processes"),
    tool("osbc_status", "Get system status"),
    tool("osbc_bot_start", "Start the bot engine"),
    tool("osbc_bot_stop", "Stop the bot engine"),
    tool("osbc_bot_status", "Get bot engine and task status"),
    tool("osbc_bot_set_task", "Set the current bot task", {
        "type": "object",
        "properties": {
            "task": {"type": "string", "enum": ["idle", "mining"]}
        },
        "required": ["task"]
    }),
    tool("osbc_auth_register", "Automate initial registration steps in Chromium", {
        "type": "object",
        "properties": {
            "email": {"type": "string"},
            "password": {"type": "string"}
        },
        "required": ["email", "password"]
    }),
    tool("osbc_vision_screenshot", "Capture and return a screenshot path"),
    tool("osbc_terminal_view", "Return an ANSI string for terminal visualization (chafa)")
]

def handle_tool_call(name, args):
    if name == "osbc_start_all":
        LAUNCHER.start_xvfb()
        LAUNCHER.start_runelite()
        return {"ok": True, "status": LAUNCHER.status()}
    
    elif name == "osbc_stop_all":
        LAUNCHER.stop_all()
        ENGINE.stop()
        return {"ok": True}
    
    elif name == "osbc_status":
        return {"launcher": LAUNCHER.status(), "bot": ENGINE.status()}
    
    elif name == "osbc_bot_start":
        ENGINE.start()
        return {"ok": True}
    
    elif name == "osbc_bot_stop":
        ENGINE.stop()
        return {"ok": True}
    
    elif name == "osbc_bot_status":
        return ENGINE.status()

    elif name == "osbc_bot_set_task":
        task_name = args.get("task")
        if task_name in TASK_MAP:
            ENGINE.set_task(TASK_MAP[task_name]())
            return {"ok": True, "task": task_name}
        return {"error": f"Task {task_name} not found"}

    elif name == "osbc_auth_register":
        email = args.get("email")
        password = args.get("password")
        LAUNCHER.start_chromium()
        time.sleep(2)
        success = asyncio.run(AUTH.run_registration_flow(email, password))
        return {"ok": success, "message": "Initial registration steps complete" if success else "Failed to start flow"}

    elif name == "osbc_vision_screenshot":
        path = LOGS / "screenshot.png"
        subprocess.run(["import", "-window", "root", str(path)], env={"DISPLAY": DISPLAY})
        return {"ok": True, "path": str(path)}

    elif name == "osbc_terminal_view":
        path = LOGS / "term_view.png"
        subprocess.run(["import", "-window", "root", str(path)], env={"DISPLAY": DISPLAY})
        res = subprocess.run(["chafa", "--size", "80x40", str(path)], capture_output=True, text=True)
        return {"ok": True, "ansi": res.stdout}

    return {"error": f"Unknown tool: {name}"}

def main():
    while True:
        line = sys.stdin.readline()
        if not line: break
        try:
            req = json.loads(line)
            if req.get("method") == "list_tools":
                resp = {"id": req.get("id"), "result": {"tools": TOOLS}}
            elif req.get("method") == "call_tool":
                params = req.get("params", {})
                result = handle_tool_call(params.get("name"), params.get("arguments", {}))
                resp = {"id": req.get("id"), "result": {"content": [{"type": "text", "text": json.dumps(result)}]}}
            else:
                resp = {"id": req.get("id"), "error": {"code": -32601, "message": "Method not found"}}
            
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")

if __name__ == "__main__":
    main()
