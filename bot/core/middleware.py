import time
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from bot.db.repositories.users_repo import UsersRepo

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self.last_requests: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            user_id = event.from_user.id

        if user_id:
            now = time.time()
            last_time = self.last_requests.get(user_id, 0)
            if now - last_time < self.rate_limit:
                # Spam bosilmoqda - e'tiborsiz qoldiramiz
                return
            self.last_requests[user_id] = now

        return await handler(event, data)


class BlockCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            user_id = event.from_user.id

        if user_id:
            user = await UsersRepo.get_by_tg_id(user_id)
            if user and user.get("status") == "blocked":
                if isinstance(event, Message):
                    await event.answer("⚠️ Sizning hisobingiz tizim qoidalarini buzganlik sababli bloklangan.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⚠️ Sizning hisobingiz bloklangan.", show_alert=True)
                return

        return await handler(event, data)
