from __future__ import annotations

import os
from dataclasses import dataclass
from typing import FrozenSet

from dotenv import load_dotenv


def _parse_ids(value: str | None) -> FrozenSet[int]:
    if not value:
        return frozenset()
    ids: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        ids.append(int(part))
    return frozenset(ids)


def _get_env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    if v is None:
        return default
    v = v.strip()
    return v if v != "" else default


def _get_int(name: str, default: int | None = None) -> int | None:
    v = _get_env(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


@dataclass(slots=True)
class Settings:
    bot_token: str
    developer_ids: str = ""
    group_chat_id: int | None = None
    db_url: str = "sqlite+aiosqlite:///./bot.db"
    log_level: str = "INFO"

    def __init__(self) -> None:
        # Load .env if exists (local/server). In some restricted environments
        # dotfiles may be unreadable; fall back to OS env vars.
        try:
            load_dotenv(".env", override=False)
        except (PermissionError, OSError):
            pass
        token = _get_env("BOT_TOKEN")
        if not token:
            raise RuntimeError("BOT_TOKEN is not set (create .env based on env.example)")
        self.bot_token = token
        self.developer_ids = _get_env("DEVELOPER_IDS", "") or ""
        self.group_chat_id = _get_int("GROUP_CHAT_ID", None)
        self.db_url = _get_env("DB_URL", "sqlite+aiosqlite:///./bot.db") or "sqlite+aiosqlite:///./bot.db"
        self.log_level = _get_env("LOG_LEVEL", "INFO") or "INFO"

    @property
    def developer_id_set(self) -> FrozenSet[int]:
        return _parse_ids(self.developer_ids)


