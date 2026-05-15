from pathlib import Path

from bobthebot.config import BotConfig
from bobthebot.processes import ProcessSupervisor


class FakeProc:
    pid = 12345


def test_start_runelite_builds_expected_command(monkeypatch, tmp_path):
    calls = []
    cfg = BotConfig(root=tmp_path, display=":77")
    supervisor = ProcessSupervisor(cfg)

    monkeypatch.setattr(supervisor, "start_xvfb", lambda: True)

    def fake_popen(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return FakeProc()

    monkeypatch.setattr("subprocess.Popen", fake_popen)

    assert supervisor.start_runelite(memory_mb=256) is True

    cmd, kwargs = calls[0]
    assert cmd == ["java", "-Xmx256m", "-jar", str(cfg.runelite_jar), "--developer-mode"]
    assert kwargs["env"]["DISPLAY"] == ":77"
    assert (cfg.runtime_dir / "runelite.pid").read_text() == "12345"


def test_start_browser_uses_configured_profile_and_debug_port(monkeypatch, tmp_path):
    calls = []
    cfg = BotConfig(root=tmp_path, display=":88", width=1024, height=768, browser_executable="/usr/bin/google-chrome", browser_debug_port=9333)
    supervisor = ProcessSupervisor(cfg)

    def fake_popen(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return FakeProc()

    monkeypatch.setattr("subprocess.Popen", fake_popen)

    assert supervisor.start_browser("https://example.test") is True

    cmd, kwargs = calls[0]
    assert "/usr/bin/google-chrome" == cmd[0]
    assert f"--remote-debugging-port={cfg.browser_debug_port}" in cmd
    assert f"--user-data-dir={cfg.browser_profile}" in cmd
    assert "--window-size=1024,768" in cmd
    assert "--headless=new" in cmd
    assert cmd[-1] == "https://example.test"
    assert Path(cfg.runtime_dir / "browser.pid").read_text() == "12345"
