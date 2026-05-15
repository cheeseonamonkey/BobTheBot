import json

from bobthebot.mcp_server import BobMcpServer


import io
import sys

from typing import Any

def call(server: BobMcpServer, method: str, params: Any = None, request_id: int = 1) -> dict[str, Any]:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        payload["params"] = params
    response = server.handle(payload)
    assert response is not None
    return response


def tool_payload(response):
    text = response["result"]["content"][0]["text"]
    return json.loads(text)


def test_initialize_exposes_tools_capability():
    response = call(BobMcpServer(), "initialize")

    assert response["result"]["serverInfo"]["name"] == "bobthebot"
    assert "tools" in response["result"]["capabilities"]


def test_tools_list_uses_mcp_method_name():
    response = call(BobMcpServer(), "tools/list")

    names = {tool["name"] for tool in response["result"]["tools"]}
    assert "bob_status" in names
    assert "bob_set_backend" in names
    assert "bob_backend_set" in names
    assert "bob_task_set" in names
    assert "bob_task_schema" in names


def test_call_status_tool_returns_structured_payload():
    response = call(
        BobMcpServer(),
        "tools/call",
        {"name": "bob_status", "arguments": {}},
    )

    payload = tool_payload(response)
    assert payload["engine"]["backend"]["backend"] == "null"
    assert payload["engine"]["backend"]["detail"]["capabilities"] == ["observe"]
    assert payload["engine"]["task"] == "idle"


def test_unknown_tool_is_marked_error():
    response = call(
        BobMcpServer(),
        "tools/call",
        {"name": "missing", "arguments": {}},
    )

    assert response["result"]["isError"] is True
    assert "Unknown tool" in tool_payload(response)["error"]


def test_tool_can_return_non_object_payload():
    from bobthebot.mcp_tools import Tool, schema

    server = BobMcpServer()
    server.tools["list_payload"] = Tool("list_payload", "Return a list payload.", schema(), lambda args: ["ok"])

    response = call(server, "tools/call", {"name": "list_payload", "arguments": {}})

    assert response["result"]["isError"] is False
    assert json.loads(response["result"]["content"][0]["text"]) == ["ok"]


def test_tool_non_json_payload_returns_tool_error():
    from bobthebot.mcp_tools import Tool, schema

    server = BobMcpServer()
    server.tools["bad_payload"] = Tool("bad_payload", "Return bad payload.", schema(), lambda args: {"bad": object()})

    response = call(server, "tools/call", {"name": "bad_payload", "arguments": {}})

    assert response["result"]["isError"] is True
    assert "non-JSON-serializable" in tool_payload(response)["error"]


def test_tool_nan_payload_returns_tool_error():
    from bobthebot.mcp_tools import Tool, schema

    server = BobMcpServer()
    server.tools["nan_payload"] = Tool("nan_payload", "Return NaN payload.", schema(), lambda args: {"bad": float("nan")})

    response = call(server, "tools/call", {"name": "nan_payload", "arguments": {}})

    assert response["result"]["isError"] is True
    assert "non-JSON-serializable" in tool_payload(response)["error"]


def test_tools_call_requires_name():
    response = call(BobMcpServer(), "tools/call", {"arguments": {}})

    assert response["result"]["isError"] is True
    assert tool_payload(response)["error"] == "Tool name is required"


def test_tools_call_reports_missing_name_before_bad_arguments():
    response = call(BobMcpServer(), "tools/call", {"arguments": []})

    assert response["result"]["isError"] is True
    assert tool_payload(response)["error"] == "Tool name is required"


def test_tools_call_rejects_non_object_arguments():
    response = call(BobMcpServer(), "tools/call", {"name": "bob_status", "arguments": []})

    assert response["result"]["isError"] is True
    assert tool_payload(response)["error"] == "bob_status: arguments must be an object"


def test_tools_call_rejects_non_object_params():
    response = call(BobMcpServer(), "tools/call", [])

    assert "error" in response
    assert response["error"]["code"] == -32600
    assert "params must be an object" in response["error"]["message"]


def test_click_error_serializes_action_result():
    response = call(
        BobMcpServer(),
        "tools/call",
        {"name": "bob_click", "arguments": {"x": 1, "y": 2}},
    )

    payload = tool_payload(response)
    assert response["result"]["isError"] is True
    assert payload["action"] == "click"
    assert payload["error"] == "null backend cannot click"


def test_incompatible_task_returns_tool_error_not_jsonrpc_error():
    response = call(
        BobMcpServer(),
        "tools/call",
        {"name": "bob_task_set", "arguments": {"task": "mining"}},
    )

    assert "error" not in response
    assert response["result"]["isError"] is True
    assert "semantic_interact" in tool_payload(response)["error"]


def test_task_config_validation_returns_tool_error():
    response = call(
        BobMcpServer(),
        "tools/call",
        {"name": "bob_task_set", "arguments": {"task": "mining", "radius": "near"}},
    )

    assert response["result"]["isError"] is True
    assert "radius must be an integer" in tool_payload(response)["error"]


def test_validation_rejects_non_finite_numbers():
    response = call(
        BobMcpServer(),
        "tools/call",
        {"name": "bob_task_set", "arguments": {"task": "mining", "cooldown": float("nan")}},
    )

    assert response["result"]["isError"] is True
    assert "cooldown must be finite" in tool_payload(response)["error"]


def test_task_schema_tool_returns_schema():
    response = call(
        BobMcpServer(),
        "tools/call",
        {"name": "bob_task_schema", "arguments": {"task": "mining"}},
    )

    payload = tool_payload(response)
    assert payload["schema"]["properties"]["cooldown"]["default"] == 5.0


def test_tool_schemas_disallow_extra_properties():
    response = call(BobMcpServer(), "tools/list")

    for tool in response["result"]["tools"]:
        if tool["name"] in ("bob_set_task", "bob_task_set"):
            assert tool["inputSchema"]["additionalProperties"] is True
        else:
            assert tool["inputSchema"]["additionalProperties"] is False


def test_validation_rejects_extra_arguments():
    response = call(
        BobMcpServer(),
        "tools/call",
        {"name": "bob_click", "arguments": {"x": 1, "y": 2, "junk": True}},
    )

    assert response["result"]["isError"] is True
    assert "unexpected argument" in tool_payload(response)["error"]


def test_validation_rejects_bad_bounds():
    response = call(
        BobMcpServer(),
        "tools/call",
        {"name": "bob_click", "arguments": {"x": -1, "y": 2}},
    )

    assert response["result"]["isError"] is True
    assert "x must be >= 0" in tool_payload(response)["error"]


def test_validation_rejects_bad_enum():
    response = call(
        BobMcpServer(),
        "tools/call",
        {"name": "bob_click", "arguments": {"x": 1, "y": 2, "button": 9}},
    )

    assert response["result"]["isError"] is True
    assert "button" in tool_payload(response)["error"]


def test_validation_rejects_empty_text():
    response = call(
        BobMcpServer(),
        "tools/call",
        {"name": "bob_type_text", "arguments": {"text": ""}},
    )

    assert response["result"]["isError"] is True
    assert "must not be empty" in tool_payload(response)["error"]


def test_null_semantic_tools_return_safe_payloads():
    server = BobMcpServer()

    player = tool_payload(call(server, "tools/call", {"name": "bob_player", "arguments": {}}))
    inventory = tool_payload(call(server, "tools/call", {"name": "bob_inventory", "arguments": {}}))
    skills = tool_payload(call(server, "tools/call", {"name": "bob_skills", "arguments": {}}))
    nearby = tool_payload(call(server, "tools/call", {"name": "bob_nearby", "arguments": {"kind": "npc"}}))

    assert "does not support player" in player["error"]
    assert "does not support inventory" in inventory["error"]
    assert "does not support skills" in skills["error"]
    assert "does not support nearby_entities" in nearby["error"]


def test_dreambot_semantic_tools_parse_state(monkeypatch):
    responses = {
        "/api/status": {"status": "running", "loggedIn": True},
        "/api/player": {
            "name": "Bob",
            "tile": {"x": 1, "y": 2, "z": 0},
            "health": 99,
            "animation": 1,
            "isMoving": False,
            "isAnimating": True,
        },
        "/api/inventory": {"count": 1, "items": [{"name": "Bronze pickaxe", "id": 1265, "amount": 1, "slot": 0}]},
        "/api/skills": {"mining": {"level": 3, "xp": 250, "boosted": 3}},
        "/api/objects": {"count": 1, "objects": [{"name": "Copper rocks"}]},
    }

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(self.payload).encode()

    def fake_urlopen(url, timeout):
        from urllib.parse import urlparse

        return FakeResponse(responses[urlparse(url).path])

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    server = BobMcpServer()
    call(server, "tools/call", {"name": "bob_backend_set", "arguments": {"backend": "dreambot"}})

    player = tool_payload(call(server, "tools/call", {"name": "bob_player", "arguments": {}}))
    inventory = tool_payload(call(server, "tools/call", {"name": "bob_inventory", "arguments": {}}))
    skills = tool_payload(call(server, "tools/call", {"name": "bob_skills", "arguments": {}}))
    nearby = tool_payload(call(server, "tools/call", {"name": "bob_nearby", "arguments": {"kind": "object"}}))

    assert player["name"] == "Bob"
    assert inventory["items"][0]["item_id"] == 1265
    assert skills["mining"]["level"] == 3
    assert nearby["objects"][0]["name"] == "Copper rocks"


def test_runtime_management_tools(monkeypatch):
    server = BobMcpServer()
    calls = []

    class MockProcesses:
        def start_xvfb(self):
            calls.append("start_xvfb")
            return {"ok": True}

        def start_runelite(self):
            calls.append("start_runelite")
            return {"ok": True}

        def stop_all(self):
            calls.append("stop_all")

        def status(self):
            return {"xvfb": True, "runelite": True}

    monkeypatch.setattr(server.app, "processes", MockProcesses())

    res = tool_payload(call(server, "tools/call", {"name": "bob_start_runtime", "arguments": {}}))
    assert res["xvfb"]["ok"] is True
    assert "start_xvfb" in calls
    assert "start_runelite" in calls

    res = tool_payload(call(server, "tools/call", {"name": "bob_stop_runtime", "arguments": {}}))
    assert res["ok"] is True
    assert "stop_all" in calls


def test_interaction_tools(monkeypatch):
    server = BobMcpServer()
    call(server, "tools/call", {"name": "bob_backend_set", "arguments": {"backend": "dreambot"}})

    calls = []

    class MockBackend:
        name = "mock"
        capabilities = ("semantic_interact", "raw_input")

        def interact(self, target):
            calls.append(("interact", target.kind, target.name, target.action, target.radius))
            from bobthebot.models import ActionResult
            return ActionResult(True, "interact", target=target.name)

        def type_text(self, text):
            calls.append(("type_text", text))
            from bobthebot.models import ActionResult
            return ActionResult(True, "type_text")

        def press_key(self, key):
            calls.append(("press_key", key))
            from bobthebot.models import ActionResult
            return ActionResult(True, "press_key")

    monkeypatch.setattr(server.app.engine, "backend", MockBackend())

    tool_payload(call(server, "tools/call", {"name": "bob_interact", "arguments": {"kind": "npc", "name": "Goblin", "action": "Attack"}}))
    assert calls[-1] == ("interact", "npc", "Goblin", "Attack", 15)

    tool_payload(call(server, "tools/call", {"name": "bob_type_text", "arguments": {"text": "hello"}}))
    assert calls[-1] == ("type_text", "hello")

    tool_payload(call(server, "tools/call", {"name": "bob_press_key", "arguments": {"key": "enter"}}))
    assert calls[-1] == ("press_key", "enter")


def test_mcp_server_ping():
    response = call(BobMcpServer(), "ping")
    assert response["result"] == {}


def test_mcp_server_notifications_ignored():
    response = BobMcpServer().handle({"jsonrpc": "2.0", "method": "notifications/test"})
    assert response is None


def test_mcp_server_serve_returns_parse_error_and_continues(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("{bad json}\n{\"jsonrpc\": \"2.0\", \"id\": 2, \"method\": \"ping\"}\n"))

    BobMcpServer().serve()

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert lines[0]["error"]["code"] == -32700
    assert lines[1] == {"jsonrpc": "2.0", "id": 2, "result": {}}


def test_mcp_server_unhandled_method_error():
    response = call(BobMcpServer(), "unknown_method")
    assert "error" in response
    assert response["error"]["code"] == -32601
    assert "Method not found" in response["error"]["message"]


def test_mcp_server_rejects_non_object_messages():
    response = BobMcpServer().handle([])
    assert response is not None

    assert response["error"]["code"] == -32600
    assert "message must be an object" in response["error"]["message"]


def test_mcp_server_rejects_missing_method():
    response = BobMcpServer().handle({"jsonrpc": "2.0", "id": 1})
    assert response is not None

    assert response["error"]["code"] == -32600
    assert "method is required" in response["error"]["message"]


def test_mcp_server_rejects_non_string_method():
    response = BobMcpServer().handle({"jsonrpc": "2.0", "id": 1, "method": 123})
    assert response is not None

    assert response["error"]["code"] == -32600
    assert "method must be a string" in response["error"]["message"]


def test_engine_state_management_tools():
    server = BobMcpServer()
    
    # Engine start
    response = call(server, "tools/call", {"name": "bob_engine_start", "arguments": {}})
    payload = tool_payload(response)
    assert payload["running"] is True
    assert payload["paused"] is False

    # Engine pause
    response = call(server, "tools/call", {"name": "bob_engine_pause", "arguments": {}})
    payload = tool_payload(response)
    assert payload["paused"] is True

    # Engine resume
    response = call(server, "tools/call", {"name": "bob_engine_resume", "arguments": {}})
    payload = tool_payload(response)
    assert payload["paused"] is False

    # Engine stop
    response = call(server, "tools/call", {"name": "bob_engine_stop", "arguments": {}})
    payload = tool_payload(response)
    assert payload["running"] is False


def test_auth_tools_dispatch_to_app_auth(monkeypatch):
    server = BobMcpServer()
    calls = []

    class MockAuthService:
        def save_credentials(self, profile, email, password):
            calls.append(("save_credentials", profile, email, password))
            return {"ok": True, "method": "save_credentials"}

        def forget_credentials(self, profile):
            calls.append(("forget_credentials", profile))
            return {"ok": True, "method": "forget_credentials"}

        def status(self, profile):
            calls.append(("status", profile))
            return {"ok": True, "method": "status"}

        def register_start(self, **kwargs):
            calls.append(("register_start", kwargs))
            return {"ok": True, "method": "register_start"}

        def login_start(self, **kwargs):
            calls.append(("login_start", kwargs))
            return {"ok": True, "method": "login_start"}

        def continue_flow(self, profile, email_code, two_factor_code):
            calls.append(("continue_flow", profile, email_code, two_factor_code))
            return {"ok": True, "method": "continue_flow"}

        def screenshot(self, profile):
            calls.append(("screenshot", profile))
            return {"ok": True, "method": "screenshot"}

        def open(self, url):
            calls.append(("open", url))
            return {"ok": True, "method": "open"}

        def verification_check(self, profile, purpose):
            calls.append(("verification_check", profile, purpose))
            return {"ok": True, "method": "verification_check"}

    monkeypatch.setattr(server.app, "auth", MockAuthService())

    res = tool_payload(call(server, "tools/call", {"name": "bob_auth_save_credentials", "arguments": {"profile": "p1", "email": "e@example.com", "password": "pass"}}))
    assert res["method"] == "save_credentials"
    assert calls[-1] == ("save_credentials", "p1", "e@example.com", "pass")

    res = tool_payload(call(server, "tools/call", {"name": "bob_auth_forget_credentials", "arguments": {"profile": "p1"}}))
    assert res["method"] == "forget_credentials"
    assert calls[-1] == ("forget_credentials", "p1")

    res = tool_payload(call(server, "tools/call", {"name": "bob_auth_status", "arguments": {"profile": "p1"}}))
    assert res["method"] == "status"
    assert calls[-1] == ("status", "p1")

    res = tool_payload(call(server, "tools/call", {"name": "bob_auth_register_start", "arguments": {"profile": "p1", "email": "e@example.com", "password": "pass", "display_name": "Bob", "submit": False}}))
    assert res["method"] == "register_start"
    assert calls[-1] == ("register_start", {"profile": "p1", "email": "e@example.com", "password": "pass", "display_name": "Bob", "submit": False})

    res = tool_payload(call(server, "tools/call", {"name": "bob_auth_login_start", "arguments": {"profile": "p1", "email": "e@example.com"}}))
    assert res["method"] == "login_start"
    assert calls[-1] == ("login_start", {"profile": "p1", "email": "e@example.com", "submit": True})

    res = tool_payload(call(server, "tools/call", {"name": "bob_auth_continue", "arguments": {"profile": "p1", "email_code": "123456"}}))
    assert res["method"] == "continue_flow"
    assert calls[-1] == ("continue_flow", "p1", "123456", None)

    res = tool_payload(call(server, "tools/call", {"name": "bob_auth_screenshot", "arguments": {"profile": "p1"}}))
    assert res["method"] == "screenshot"
    assert calls[-1] == ("screenshot", "p1")

    res = tool_payload(call(server, "tools/call", {"name": "bob_auth_open", "arguments": {"url": "https://example.com"}}))
    assert res["method"] == "open"
    assert calls[-1] == ("open", "https://example.com")

    res = tool_payload(call(server, "tools/call", {"name": "bob_auth_verification_check", "arguments": {"profile": "p1", "purpose": "auth"}}))
    assert res["method"] == "verification_check"
    assert calls[-1] == ("verification_check", "p1", "auth")


def test_auth_save_credentials_redacts_password(tmp_path):
    from bobthebot.app import BotApp
    from bobthebot.config import BotConfig

    server = BobMcpServer(BotApp(config=BotConfig(root=tmp_path)))
    response = call(
        server,
        "tools/call",
        {"name": "bob_auth_save_credentials", "arguments": {"profile": "main", "email": "a@example.test", "password": "secret"}},
    )

    payload = tool_payload(response)
    assert payload["has_password"] is True
    assert "secret" not in json.dumps(response)


def test_auth_tool_validation_supports_boolean_submit(tmp_path):
    from bobthebot.app import BotApp
    from bobthebot.config import BotConfig

    server = BobMcpServer(BotApp(config=BotConfig(root=tmp_path)))
    response = call(
        server,
        "tools/call",
        {"name": "bob_auth_register_start", "arguments": {"submit": "yes"}},
    )

    assert response["result"]["isError"] is True
    assert "submit must be a boolean" in tool_payload(response)["error"]
