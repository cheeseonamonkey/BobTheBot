from __future__ import annotations

from ._base import ToolGroup, Tool, register, schema

_profile = {"profile": {"type": "string", "default": "default", "minLength": 1}}
_credential = {
    "profile": {"type": "string", "default": "default", "minLength": 1},
    "email": {"type": "string", "minLength": 1},
    "password": {"type": "string", "minLength": 1},
}
_auth_start = {
    "profile": {"type": "string", "default": "default", "minLength": 1},
    "email": {"type": "string", "minLength": 1},
    "password": {"type": "string", "minLength": 1},
    "display_name": {"type": "string", "minLength": 1},
    "submit": {"type": "boolean", "default": True},
}
_auth_continue = {
    "profile": {"type": "string", "default": "default", "minLength": 1},
    "email_code": {"type": "string", "minLength": 1},
    "two_factor_code": {"type": "string", "minLength": 1},
}
_verify = {
    "profile": {"type": "string", "default": "default", "minLength": 1},
    "purpose": {"type": "string", "default": "auth", "minLength": 1},
}


@register
class AuthTools(ToolGroup):
    def tools(self) -> list[Tool]:
        return [
            Tool("bob_auth_save_credentials",
                 "Persist plaintext auth credentials for a profile.",
                 schema(_credential, ["email", "password"]),
                 self._save_credentials),
            Tool("bob_auth_forget_credentials",
                 "Forget saved auth credentials for a profile.",
                 schema(_profile),
                 lambda args: self.app.auth_forget_credentials(str(args.get("profile", "default")))),
            Tool("bob_auth_status",
                 "Return current browser auth status.",
                 schema(_profile),
                 lambda args: self.app.auth_status(str(args.get("profile", "default")))),
            Tool("bob_auth_register_start",
                 "Start automated Jagex registration (opens visible Chrome).",
                 schema(_auth_start),
                 lambda args: self.app.auth_register_start(**self._start_args(args))),
            Tool("bob_auth_login_start",
                 "Start automated Jagex login (opens visible Chrome).",
                 schema(_auth_start),
                 lambda args: self.app.auth_login_start(**self._start_args(args))),
            Tool("bob_auth_continue",
                 "Submit an email or two-factor code when requested.",
                 schema(_auth_continue),
                 self._continue),
            Tool("bob_auth_screenshot",
                 "Capture current auth browser screenshot.",
                 schema(_profile),
                 lambda args: self.app.auth_screenshot(str(args.get("profile", "default")))),
            Tool("bob_auth_open",
                 "Open an arbitrary URL in the auth browser.",
                 schema({"url": {"type": "string", "minLength": 1}}, ["url"]),
                 lambda args: self.app.auth_open(str(args["url"]))),
            Tool("bob_auth_verification_check",
                 "Check configured verification providers for a code.",
                 schema(_verify),
                 lambda args: self.app.auth_verification_check(
                     profile=str(args.get("profile", "default")),
                     purpose=str(args.get("purpose", "auth")),
                 )),
            Tool("bob_auth_guide_step",
                 "Screenshot + state analysis. Returns what is on screen, visible buttons/inputs, needs_user flag, and suggested_action. Primary tool for driving the auth loop.",
                 schema(_profile),
                 lambda args: self.app.auth_guide_step(str(args.get("profile", "default")))),
            Tool("bob_auth_wait",
                 "Poll the browser until one of the target states is reached or timeout expires.",
                 schema({
                     "profile": {"type": "string", "default": "default", "minLength": 1},
                     "target_states": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                     "timeout": {"type": "number", "default": 30.0, "minimum": 1.0, "maximum": 300.0},
                 }, ["target_states"]),
                 self._wait),
            Tool("bob_auth_click_text",
                 "Click the first button or link whose visible text contains the given string.",
                 schema({"text": {"type": "string", "minLength": 1}}, ["text"]),
                 lambda args: self.app.auth_click_text(str(args["text"]))),
            Tool("bob_auth_restart_browser",
                 "Kill any running browser instance and open a fresh visible Chrome at a URL.",
                 schema({"url": {"type": "string", "minLength": 1}}),
                 lambda args: self.app.auth_restart_browser(url=args.get("url"))),
        ]

    def _save_credentials(self, args: dict) -> dict:
        return self.app.auth_save_credentials(
            profile=str(args.get("profile", "default")),
            email=str(args["email"]),
            password=str(args["password"]),
        )

    def _continue(self, args: dict) -> dict:
        return self.app.auth_continue(
            profile=str(args.get("profile", "default")),
            email_code=args.get("email_code"),
            two_factor_code=args.get("two_factor_code"),
        )

    def _start_args(self, args: dict) -> dict:
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

    def _wait(self, args: dict) -> dict:
        return self.app.auth_wait(
            target_states=[str(s) for s in args["target_states"]],
            timeout=float(args.get("timeout", 30.0)),
        )
