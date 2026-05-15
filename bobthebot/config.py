from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BotConfig:
    root: Path
    display: str = ":99"
    width: int = 800
    height: int = 600
    depth: int = 24
    tick_rate: float = 0.5
    dreambot_url: str = "http://127.0.0.1:19132"
    browser_executable: str | None = None
    browser_debug_port: int = 9222
    jagex_register_url: str = "https://account.jagex.com/en-GB/sign-up"
    jagex_login_url: str = "https://account.jagex.com/en-GB/login"
    email_code_command: str | None = None
    imap_host: str | None = None
    imap_user: str | None = None
    imap_password: str | None = None
    imap_mailbox: str = "INBOX"

    @property
    def runtime_dir(self) -> Path:
        return self.root / ".runtime"

    @property
    def logs_dir(self) -> Path:
        return self.runtime_dir / "logs"

    @property
    def config_dir(self) -> Path:
        return self.runtime_dir / "config"

    @property
    def runelite_jar(self) -> Path:
        return self.root / "osbc" / "RuneLite.jar"

    @property
    def browser_profile(self) -> Path:
        return self.config_dir / "browser-profile"

    

    @property
    def auth_dir(self) -> Path:
        return self.runtime_dir / "auth"

    @property
    def auth_credentials_file(self) -> Path:
        return self.auth_dir / "credentials.json"

    def ensure_dirs(self) -> None:
        for path in (self.runtime_dir, self.logs_dir, self.config_dir, self.auth_dir):
            path.mkdir(parents=True, exist_ok=True)


def default_config() -> BotConfig:
    root = Path(os.getenv("BOBTHEBOT_ROOT", Path(__file__).resolve().parent.parent))
    cfg = BotConfig(
        root=root,
        display=os.getenv("BOBTHEBOT_DISPLAY", os.getenv("OSBC_DISPLAY", ":99")),
        width=int(os.getenv("BOBTHEBOT_WIDTH", "800")),
        height=int(os.getenv("BOBTHEBOT_HEIGHT", "600")),
        depth=int(os.getenv("BOBTHEBOT_DEPTH", "24")),
        tick_rate=float(os.getenv("BOBTHEBOT_TICK_RATE", "0.5")),
        dreambot_url=os.getenv("BOBTHEBOT_DREAMBOT_URL", "http://127.0.0.1:19132"),
        browser_executable=os.getenv("BOBTHEBOT_BROWSER"),
        browser_debug_port=int(os.getenv("BOBTHEBOT_BROWSER_PORT", "9222")),
        jagex_register_url=os.getenv("BOBTHEBOT_JAGEX_REGISTER_URL", "https://account.jagex.com/en-GB/sign-up"),
        jagex_login_url=os.getenv("BOBTHEBOT_JAGEX_LOGIN_URL", "https://account.jagex.com/en-GB/login"),
        email_code_command=os.getenv("BOBTHEBOT_EMAIL_CODE_COMMAND"),
        imap_host=os.getenv("BOBTHEBOT_IMAP_HOST"),
        imap_user=os.getenv("BOBTHEBOT_IMAP_USER"),
        imap_password=os.getenv("BOBTHEBOT_IMAP_PASSWORD"),
        imap_mailbox=os.getenv("BOBTHEBOT_IMAP_MAILBOX", "INBOX"),
    )
    cfg.ensure_dirs()
    return cfg
