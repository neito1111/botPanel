from __future__ import annotations

import logging

from sqlalchemy import text

from bot.config import Settings
from bot.db import make_engine, make_sessionmaker, session_scope
from bot.logging_setup import setup_logging
from bot.models import Base
from bot.repositories import ensure_default_banks, list_banks, list_team_leads


async def run_doctor() -> int:
    """
    Offline self-check:
    - loads .env
    - validates basic settings
    - initializes DB schema
    - ensures default banks exist
    """
    settings = Settings()
    setup_logging(settings.log_level)
    log = logging.getLogger("doctor")

    problems: list[str] = []

    if not settings.bot_token or ":" not in settings.bot_token:
        problems.append("BOT_TOKEN выглядит некорректно (ожидается формат '123:ABC')")
    if not settings.developer_id_set:
        problems.append("DEVELOPER_IDS пустой — запросы доступа некому апрувить")
    if not settings.group_chat_id:
        problems.append("GROUP_CHAT_ID не задан — подтвержденные анкеты не будут уходить в группу")

    engine = make_engine(settings.db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("SELECT 1"))

    session_maker = make_sessionmaker(engine)
    async with session_scope(session_maker) as session:
        await ensure_default_banks(session)
        banks = await list_banks(session)
        tls = await list_team_leads(session)

    if not tls:
        problems.append("В БД нет тим‑лидов — анкеты некому проверять (добавьте в панели разработчика → Тим‑лиды)")

    log.info("OK: settings loaded, DB initialized")
    log.info("Developer IDs: %s", sorted(settings.developer_id_set))
    log.info("Team leads in DB: %s", [(t.tg_id, str(t.source)) for t in tls])
    log.info("Group chat id: %s", settings.group_chat_id)
    log.info("DB url: %s", settings.db_url)
    log.info("Banks in DB: %s", [b.name for b in banks])

    if problems:
        for p in problems:
            log.warning("PROBLEM: %s", p)
        return 2

    return 0


