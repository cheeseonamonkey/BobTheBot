import json
import os
import subprocess

from bobthebot.auth import AuthService, CredentialStore
from bobthebot.auth_verification import CommandVerificationProvider, ImapVerificationProvider, extract_verification_code
from bobthebot.config import BotConfig


class FakeProcesses:
    def __init__(self):
        self.urls = []

    def start_browser(self, url=None):
        self.urls.append(url)
        return True


class FakeBrowser:
    def __init__(self, snapshot=None):
        self.snapshot = snapshot or {"url": "https://account.jagex.com/en-GB/sign-up", "title": "Sign up", "text": ""}
        self.filled = []
        self.clicked = []
        self.navigated = []

    async def navigate(self, url):
        self.navigated.append(url)
        self.snapshot["url"] = url
        return self.snapshot

    async def fill_first(self, selectors, text):
        self.filled.append((selectors, text))
        return True

    async def click_first(self, selectors):
        self.clicked.append(selectors)
        return True

    async def page_snapshot(self):
        return self.snapshot

    async def screenshot(self, path):
        path.write_bytes(b"png")
        return path


def test_credential_store_persists_plaintext_with_redacted_result(tmp_path):
    store = CredentialStore(tmp_path / "credentials.json")

    result = store.save("main", "a@example.test", "secret")

    assert result == {"ok": True, "profile": "main", "email": "a@example.test", "has_password": True}
    assert "secret" in (tmp_path / "credentials.json").read_text()
    assert oct(os.stat(tmp_path / "credentials.json").st_mode & 0o777) == "0o600"
    assert store.load("main") == {"email": "a@example.test", "password": "secret"}


def test_auth_detects_verification_and_captcha_states(tmp_path):
    service = AuthService(BotConfig(root=tmp_path), FakeProcesses(), FakeBrowser())

    email = service.detect_state({"url": "https://x", "text": "Check your email for a verification code"})
    captcha = service.detect_state({"url": "https://x", "text": "Verify you are human with CAPTCHA"})

    assert email.state == "awaiting_email_code"
    assert email.needs == ["email_code"]
    assert captcha.state == "awaiting_captcha"


def test_extract_verification_code_accepts_six_to_eight_digits():
    assert extract_verification_code("Your Jagex verification code is 123456.") == "123456"
    assert extract_verification_code("code: 12345678") == "12345678"
    assert extract_verification_code("no code here") is None


def test_command_verification_provider_extracts_stdout_code(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs["env"]))
        return subprocess.CompletedProcess(command, 0, stdout="Jagex code: 654321", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    code = CommandVerificationProvider("fetch-code").fetch_code("main", "a@example.test", "register")

    assert code == "654321"
    assert calls[0][1]["BOBTHEBOT_PROFILE"] == "main"
    assert calls[0][1]["BOBTHEBOT_EMAIL"] == "a@example.test"
    assert calls[0][1]["BOBTHEBOT_PURPOSE"] == "register"


def test_imap_verification_provider_is_inert_without_config():
    provider = ImapVerificationProvider(None, "user", "password")

    assert provider.fetch_code("main", "a@example.test", "auth") is None


def test_register_start_fills_credentials_and_submits(tmp_path):
    browser = FakeBrowser({"url": "https://account.jagex.com/en-GB/sign-up", "title": "Sign up", "text": "Create account"})
    processes = FakeProcesses()
    service = AuthService(BotConfig(root=tmp_path), processes, browser)

    result = service.register_start(profile="main", email="a@example.test", password="secret", display_name="Bob")

    assert result["state"] == "registration_page"
    assert processes.urls == ["https://account.jagex.com/en-GB/sign-up"]
    assert any(item[1] == "a@example.test" for item in browser.filled)
    assert any(item[1] == "secret" for item in browser.filled)
    assert browser.clicked
    assert result["data"]["email_filled"] is True
    assert result["data"]["password_filled"] is True
    assert result["data"]["display_name_filled"] is True
    assert result["data"]["submit_clicked"] is True
    assert "secret" not in json.dumps(result)


def test_register_start_reports_captcha_with_screenshot(tmp_path):
    browser = FakeBrowser({"url": "https://account.jagex.com/en-GB/sign-up", "title": "Sign up", "text": "CAPTCHA verify you are human"})
    service = AuthService(BotConfig(root=tmp_path), FakeProcesses(), browser)

    result = service.register_start(profile="main", email="a@example.test", password="secret")

    assert result["state"] == "awaiting_captcha"
    assert result["needs"] == ["captcha"]
    assert result["screenshot"].endswith("auth-latest.png")
    assert result["data"]["email_filled"] is True


def test_continue_flow_uses_env_verification_code(tmp_path, monkeypatch):
    browser = FakeBrowser({"url": "https://account.jagex.com/en-GB/login", "title": "Login", "text": "Welcome"})
    service = AuthService(BotConfig(root=tmp_path), FakeProcesses(), browser)
    service.save_credentials("main", "a@example.test", "secret")
    monkeypatch.setenv("BOBTHEBOT_EMAIL_CODE", "123456")

    result = service.continue_flow("main")

    assert result["state"] == "logged_in"
    assert any(item[1] == "123456" for item in browser.filled)


def test_screenshot_returns_path(tmp_path):
    service = AuthService(BotConfig(root=tmp_path), FakeProcesses(), FakeBrowser())

    result = service.screenshot("main")

    assert result["ok"] is True
    assert result["path"].endswith("auth-main.png")


def test_open_returns_detected_auth_state(tmp_path):
    browser = FakeBrowser({"url": "https://account.jagex.com/en-GB/sign-up", "title": "Just a moment", "text": "Are you a robot? CAPTCHA"})
    service = AuthService(BotConfig(root=tmp_path), FakeProcesses(), browser)

    result = service.open("https://account.jagex.com/en-GB/sign-up")

    assert result["ok"] is True
    assert result["auth_state"]["state"] == "awaiting_captcha"
