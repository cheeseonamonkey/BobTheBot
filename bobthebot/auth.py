from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .browser import BrowserController
from .config import BotConfig
from .processes import ProcessSupervisor
from .auth_verification import (
    CommandVerificationProvider,
    CompositeVerificationProvider,
    EnvVerificationProvider,
    ImapVerificationProvider,
    VerificationProvider,
)


EMAIL_SELECTORS = ['input[type="email"]', 'input[name="email"]', '#email']
PASSWORD_SELECTORS = ['input[type="password"]', 'input[name="password"]', '#password']
SUBMIT_SELECTORS = ['button[type="submit"]', 'input[type="submit"]', 'button[data-testid*="submit"]']
DISPLAY_NAME_SELECTORS = ['input[name="displayName"]', 'input[name="display_name"]', '#displayName']
AUTH_STATE_RULES = (
    ("awaiting_cloudflare", False, "Cloudflare challenge detected.", ["captcha"], ("just a moment", "checking your browser", "enable javascript and cookies", "cf-challenge-running")),
    ("awaiting_captcha", False, "CAPTCHA or security check detected.", ["captcha"], ("captcha", "turnstile", "verify you are human", "security check", "cloudflare")),
    ("awaiting_email_code", False, "Email verification code required.", ["email_code"], ("verification code", "email code", "check your email", "enter the code")),
    ("awaiting_2fa", False, "Two-factor code required.", ["two_factor_code"], ("authenticator", "two-factor", "two factor", "2fa")),
    ("blocked", False, "Registration/login appears blocked or rate-limited.", None, ("blocked", "too many attempts", "temporarily unavailable")),
    ("logged_in", True, "Account appears authenticated.", None, ("account created", "welcome", "logout", "log out")),
)

_GUIDE_HINTS: dict[str, tuple[bool, str]] = {
    "registration_page": (False, "Fill email/password fields, then click the submit button"),
    "login_page": (False, "Fill email/password fields, then click sign in"),
    "awaiting_cloudflare": (True, "Ask the user to solve the Cloudflare challenge in the Chrome window, then call bob_auth_guide_step again"),
    "awaiting_captcha": (True, "Ask the user to solve the CAPTCHA in the Chrome window, then call bob_auth_guide_step again"),
    "awaiting_email_code": (True, "Ask the user for the email OTP code, then call bob_auth_continue with email_code=<code>"),
    "awaiting_2fa": (True, "Ask the user for the 2FA code, then call bob_auth_continue with two_factor_code=<code>"),
    "logged_in": (False, "Authentication complete"),
    "unknown": (False, "Inspect the screenshot to decide the next action"),
}


@dataclass(frozen=True)
class AuthResult:
    ok: bool
    state: str
    message: str
    url: str | None = None
    screenshot: str | None = None
    needs: list[str] | None = None
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


class CredentialStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, profile: str, email: str, password: str) -> dict[str, Any]:
        data = self._read()
        data[profile] = {"email": email, "password": password, "updated_at": time.time()}
        self.path.write_text(json.dumps(data, indent=2))
        os.chmod(self.path, 0o600)
        return {"ok": True, "profile": profile, "email": email, "has_password": True}

    def load(self, profile: str) -> dict[str, str] | None:
        value = self._read().get(profile)
        if not isinstance(value, dict):
            return None
        if not value.get("email") or not value.get("password"):
            return None
        return {"email": str(value["email"]), "password": str(value["password"])}

    def forget(self, profile: str) -> dict[str, Any]:
        data = self._read()
        existed = profile in data
        data.pop(profile, None)
        self.path.write_text(json.dumps(data, indent=2))
        os.chmod(self.path, 0o600)
        return {"ok": True, "profile": profile, "existed": existed}

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text())
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}


class AuthService:
    def __init__(
        self,
        config: BotConfig,
        processes: ProcessSupervisor,
        browser: BrowserController | None = None,
        credentials: CredentialStore | None = None,
        verification: VerificationProvider | None = None,
    ):
        self.config = config
        self.config.ensure_dirs()
        self.processes = processes
        self.browser = browser or BrowserController(config)
        self.credentials = credentials or CredentialStore(config.auth_credentials_file)
        self.verification = verification or CompositeVerificationProvider(
            [
                EnvVerificationProvider(),
                CommandVerificationProvider(config.email_code_command),
                ImapVerificationProvider(config.imap_host, config.imap_user, config.imap_password, config.imap_mailbox),
            ]
        )

    def save_credentials(self, profile: str, email: str, password: str) -> dict[str, Any]:
        return self.credentials.save(profile, email, password)

    def forget_credentials(self, profile: str) -> dict[str, Any]:
        return self.credentials.forget(profile)

    def status(self, profile: str = "default") -> dict[str, Any]:
        creds = self.credentials.load(profile)
        try:
            snapshot = asyncio.run(self.browser.page_snapshot())
            state = self.detect_state(snapshot)
        except Exception as exc:
            return {
                "ok": False,
                "profile": profile,
                "has_credentials": creds is not None,
                "state": "browser_unavailable",
                "message": str(exc),
            }
        return {
            "ok": True,
            "profile": profile,
            "has_credentials": creds is not None,
            **state.to_dict(),
        }

    def register_start(self, profile: str = "default", **kwargs: Any) -> dict[str, Any]:
        return self._start_flow("register", profile, self.config.jagex_register_url, **kwargs).to_dict()

    def login_start(self, profile: str = "default", **kwargs: Any) -> dict[str, Any]:
        return self._start_flow("login", profile, self.config.jagex_login_url, **kwargs).to_dict()

    def continue_flow(self, profile: str = "default", email_code: str | None = None, two_factor_code: str | None = None) -> dict[str, Any]:
        creds = self._credentials(profile, None, None)
        code = email_code or two_factor_code
        if not code and creds:
            code = self.verification.fetch_code(profile, creds["email"], "auth")
        if not code:
            return self._snapshot_result("awaiting_code", "No verification code available.", needs=["email_code", "two_factor_code"]).to_dict()
        asyncio.run(self._fill_code_and_submit(code))
        return self._snapshot_result("submitted", "Verification code submitted.").to_dict()

    def screenshot(self, profile: str = "default") -> dict[str, Any]:
        path = self.config.logs_dir / f"auth-{profile}.png"
        try:
            result = asyncio.run(self.browser.screenshot(path))
            return {"ok": True, "profile": profile, "path": str(result)}
        except Exception as exc:
            return {"ok": False, "profile": profile, "error": str(exc)}

    def wait_for_state(self, target_states: list[str], timeout: float = 30.0, poll: float = 1.0) -> dict[str, Any]:
        deadline = time.time() + timeout
        last: AuthResult | None = None
        while time.time() < deadline:
            try:
                snapshot = asyncio.run(self.browser.page_snapshot())
                last = self.detect_state(snapshot)
                if last.state in target_states:
                    return {"ok": True, "reached": True, **last.to_dict()}
            except Exception:
                pass
            time.sleep(poll)
        if last:
            return {"ok": True, "reached": False, "timed_out": True, **last.to_dict()}
        return {"ok": False, "reached": False, "timed_out": True, "state": "browser_unavailable"}

    def guide_step(self, profile: str = "default") -> dict[str, Any]:
        path = self.config.logs_dir / f"auth-{profile}.png"
        try:
            async def _collect():
                snapshot = await self.browser.page_snapshot()
                buttons = await self.browser.visible_buttons()
                inputs = await self.browser.visible_inputs()
                screenshot_path = await self.browser.screenshot(path)
                return snapshot, buttons, inputs, screenshot_path

            snapshot, buttons, inputs, screenshot_path = asyncio.run(_collect())
        except Exception as exc:
            return {"ok": False, "state": "browser_unavailable", "message": str(exc), "needs_user": False}

        detected = self.detect_state(snapshot)
        needs_user, suggested_action = _GUIDE_HINTS.get(detected.state, (False, "Inspect the screenshot to decide the next action"))
        return {
            "ok": detected.ok,
            "state": detected.state,
            "message": detected.message,
            "url": snapshot.get("url"),
            "screenshot": str(screenshot_path),
            "visible_buttons": buttons,
            "visible_inputs": inputs,
            "needs_user": needs_user,
            "suggested_action": suggested_action,
        }

    def click_text(self, text: str) -> dict[str, Any]:
        try:
            clicked = asyncio.run(self.browser.click_text(text))
            return {"ok": clicked, "clicked": clicked, "text": text}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def restart_browser(self, url: str | None = None) -> dict[str, Any]:
        ok = self.processes.restart_browser(url=url, headless=False)
        return {"ok": ok, "url": url}

    def open(self, url: str) -> dict[str, Any]:
        self.processes.start_browser(url)
        snapshot = asyncio.run(self.browser.navigate(url))
        return {"ok": True, **snapshot, "auth_state": self.detect_state(snapshot).to_dict()}

    def verification_check(self, profile: str = "default", purpose: str = "auth") -> dict[str, Any]:
        creds = self._credentials(profile, None, None)
        if not creds:
            return {"ok": False, "state": "missing_credentials", "message": "No credentials saved for profile."}
        code = self.verification.fetch_code(profile, creds["email"], purpose)
        return {"ok": code is not None, "profile": profile, "has_code": code is not None}

    def _start_flow(self, mode: str, profile: str, url: str, **kwargs: Any) -> AuthResult:
        creds = self._credentials(profile, kwargs.get("email"), kwargs.get("password"))
        if not creds:
            return AuthResult(False, "missing_credentials", "Provide email/password or save credentials first.")
        self.processes.start_browser(url, headless=False)

        async def _flow() -> dict[str, Any]:
            await self.browser.navigate(url)
            fill = await self._fill_credentials(creds["email"], creds["password"], kwargs)
            if kwargs.get("submit", True):
                fill["submit_clicked"] = await self.browser.click_first(SUBMIT_SELECTORS)
                await asyncio.sleep(1.0)
            return fill

        fill_result = asyncio.run(_flow())
        state = self._snapshot_result("submitted", f"{mode} flow submitted.")
        if state.state == "awaiting_email_code":
            code = self.verification.fetch_code(profile, creds["email"], mode)
            if code:
                return AuthResult(True, "email_code_available", "Verification code found; call continue or let next step submit it.", data={"has_code": True})
        return self._with_data(state, fill_result)

    async def _fill_credentials(self, email: str, password: str, values: dict[str, Any]) -> dict[str, bool]:
        result = {
            "email_filled": await self.browser.fill_first(EMAIL_SELECTORS, email),
            "password_filled": await self.browser.fill_first(PASSWORD_SELECTORS, password),
        }
        if values.get("display_name"):
            result["display_name_filled"] = await self.browser.fill_first(DISPLAY_NAME_SELECTORS, str(values["display_name"]))
        return result

    async def _fill_code_and_submit(self, code: str) -> None:
        selectors = ['input[name*="code"]', 'input[autocomplete="one-time-code"]', 'input[type="tel"]', 'input[type="text"]']
        await self.browser.fill_first(selectors, code)
        await self.browser.click_first(SUBMIT_SELECTORS)

    def _snapshot_result(self, fallback_state: str, message: str, needs: list[str] | None = None) -> AuthResult:
        try:
            snapshot = asyncio.run(self.browser.page_snapshot())
            detected = self.detect_state(snapshot)
            if detected.state != "unknown":
                return self._with_screenshot(detected) if detected.needs else detected
            return AuthResult(True, fallback_state, message, url=snapshot.get("url"), needs=needs, data={"title": snapshot.get("title")})
        except Exception as exc:
            return AuthResult(False, "error", str(exc))

    def _with_screenshot(self, result: AuthResult) -> AuthResult:
        path = self.screenshot("latest").get("path")
        return AuthResult(result.ok, result.state, result.message, result.url, path, result.needs, result.data)

    def _with_data(self, result: AuthResult, data: dict[str, Any]) -> AuthResult:
        merged = {**(result.data or {}), **data}
        return AuthResult(result.ok, result.state, result.message, result.url, result.screenshot, result.needs, merged)

    def detect_state(self, snapshot: dict[str, Any]) -> AuthResult:
        text = str(snapshot.get("text") or "").lower()
        url = str(snapshot.get("url") or "")
        for state, ok, message, needs, terms in AUTH_STATE_RULES:
            if any(term in text for term in terms):
                return AuthResult(ok, state, message, url=url, needs=needs)
        if url_state := self._detect_url_state(url):
            return url_state
        return AuthResult(True, "unknown", "Unable to classify auth page.", url=url)

    def _detect_url_state(self, url: str) -> AuthResult | None:
        if "sign-up" in url or "create" in url:
            return AuthResult(True, "registration_page", "Registration page is open.", url=url)
        if "login" in url:
            return AuthResult(True, "login_page", "Login page is open.", url=url)
        return None

    def _credentials(self, profile: str, email: str | None, password: str | None) -> dict[str, str] | None:
        if email and password:
            self.credentials.save(profile, email, password)
            return {"email": email, "password": password}
        return self.credentials.load(profile)
