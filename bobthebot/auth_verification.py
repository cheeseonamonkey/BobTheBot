from __future__ import annotations

import imaplib
import os
import re
import subprocess
from email import message_from_bytes
from email.message import Message


CODE_RE = re.compile(r"\b(\d{6,8})\b")


def extract_verification_code(text: str) -> str | None:
    match = CODE_RE.search(text)
    return match.group(1) if match else None


class VerificationProvider:
    def fetch_code(self, profile: str, email: str, purpose: str) -> str | None:
        return None


class EnvVerificationProvider(VerificationProvider):
    def fetch_code(self, profile: str, email: str, purpose: str) -> str | None:
        return os.getenv("BOBTHEBOT_EMAIL_CODE") or os.getenv(f"BOBTHEBOT_EMAIL_CODE_{profile.upper()}")


class CommandVerificationProvider(VerificationProvider):
    def __init__(self, command: str | None):
        self.command = command

    def fetch_code(self, profile: str, email: str, purpose: str) -> str | None:
        if not self.command:
            return None
        env = os.environ.copy()
        env.update({"BOBTHEBOT_PROFILE": profile, "BOBTHEBOT_EMAIL": email, "BOBTHEBOT_PURPOSE": purpose})
        proc = subprocess.run(self.command, shell=True, env=env, capture_output=True, text=True, timeout=20)
        if proc.returncode != 0:
            return None
        return extract_verification_code(proc.stdout)


class ImapVerificationProvider(VerificationProvider):
    def __init__(self, host: str | None, user: str | None, password: str | None, mailbox: str = "INBOX"):
        self.host = host
        self.user = user
        self.password = password
        self.mailbox = mailbox

    def fetch_code(self, profile: str, email: str, purpose: str) -> str | None:
        if not all((self.host, self.user, self.password)):
            return None
        with imaplib.IMAP4_SSL(str(self.host)) as client:
            client.login(str(self.user), str(self.password))
            client.select(self.mailbox)
            _, data = client.search(None, "ALL")
            ids = data[0].split()[-20:] if data and data[0] else []
            for msg_id in reversed(ids):
                if code := self._code_from_message(client, msg_id):
                    return code
        return None

    def _code_from_message(self, client: imaplib.IMAP4_SSL, msg_id: bytes) -> str | None:
        _, data = client.fetch(msg_id, "(RFC822)")
        if not data or not isinstance(data[0], tuple):
            return None
        msg = message_from_bytes(data[0][1])
        text = self._message_text(msg)
        if not self._looks_relevant(msg, text):
            return None
        return extract_verification_code(text)

    def _message_text(self, msg: Message) -> str:
        if msg.is_multipart():
            parts = [part.get_payload(decode=True) for part in msg.walk() if part.get_content_maintype() == "text"]
            return "\n".join(part.decode(errors="ignore") for part in parts if part)
        payload = msg.get_payload(decode=True)
        return payload.decode(errors="ignore") if payload else str(msg.get_payload())

    def _looks_relevant(self, msg: Message, text: str) -> bool:
        haystack = " ".join([msg.get("from", ""), msg.get("subject", ""), text]).lower()
        return any(term in haystack for term in ("jagex", "runescape", "verification", "code"))


class CompositeVerificationProvider(VerificationProvider):
    def __init__(self, providers: list[VerificationProvider]):
        self.providers = providers

    def fetch_code(self, profile: str, email: str, purpose: str) -> str | None:
        for provider in self.providers:
            if code := provider.fetch_code(profile, email, purpose):
                return code
        return None
