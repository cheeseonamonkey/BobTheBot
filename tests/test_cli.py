import json
import subprocess
from pathlib import Path

from bobthebot import cli


def test_cli_tasks_outputs_task_list(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["bobthebot-run", "tasks"])

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["tasks"][0]["name"] == "idle"


def test_cli_tool_invokes_mcp_tool(capsys, monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["bobthebot-run", "tool", "bob_task_schema", "--args", '{"task": "idle"}'],
    )

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["task"] == "idle"


def test_cli_tool_accepts_key_value_args(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["bobthebot-run", "tool", "bob_task_schema", "task=idle"])

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["task"] == "idle"


def test_cli_tools_lists_tool_names(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["bobthebot-run", "tools"])

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    names = {tool["name"] for tool in payload["tools"]}
    assert "bob_status" in names
    assert "bob_auth_status" in names


def test_cli_doctor_reports_dense_sanity(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["bobthebot-run", "doctor", "--renderer", "none"])

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert "checks" in payload
    assert "executables" in payload
    assert "next" in payload


def test_cli_demo_view_generates_renderable_image(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["bobthebot-run", "demo-view", "--renderer", "none"])

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["path"].endswith("demo-view.png")
    assert Path(payload["path"]).exists()


def test_is_image_path_accepts_ppm():
    assert cli.is_image_path("demo-view.ppm") is True


def test_render_image_uses_chafa_when_available(monkeypatch):
    calls = []

    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/chafa" if name == "chafa" else None)

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    rendered = cli.render_image(Path("/tmp/screen.png"))

    assert rendered is True
    assert calls[0][0] == ["/usr/bin/chafa", "--symbols", "block", "--size", "100x40", "/tmp/screen.png"]
    assert calls[0][1]["stdout"] is cli.sys.stderr


def test_render_image_none_skips_renderer(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/chafa")

    assert cli.render_image(Path("/tmp/screen.png"), "none") is False
