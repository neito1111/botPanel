from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select

from bot.models import User


class DBSessionMiddleware(BaseMiddleware):
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        super().__init__()
        self._session_maker = session_maker

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with self._session_maker() as session:
            data["session"] = session
            result = await handler(event, data)
            await session.commit()
            return result


class GroupChatRestrictionMiddleware(BaseMiddleware):
    """
    Restricts bot activity in group chats.
    Only allows the bot to operate in private chats or be completely silent in groups.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Check if this is a message from a group chat
        if hasattr(event, 'chat') and event.chat.type in ['group', 'supergroup']:
            # Completely ignore all messages in group chats
            # The bot should only send messages to groups, not respond to them
            return None
        
        # For private chats, proceed normally
        return await handler(event, data)


class LastPrivateMessageTrackerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        session = data.get("session")
        if isinstance(session, AsyncSession):
            msg = event if isinstance(event, Message) else getattr(event, "message", None)
            if isinstance(msg, Message) and msg.chat and msg.chat.type == "private" and msg.from_user:
                try:
                    res = await session.execute(select(User).where(User.tg_id == int(msg.from_user.id)))
                    u = res.scalar_one_or_none()
                    if u:
                        u.last_private_message_id = int(msg.message_id)
                        u.last_private_message_at = msg.date
                except Exception:
                    pass
        return await handler(event, data)


class GroupMessageFilter:
    """
    Filter that can be used to block group messages at the router level.
    """
    
    def __call__(self, message: Message) -> bool:
        return message.chat.type not in ['group', 'supergroup']
