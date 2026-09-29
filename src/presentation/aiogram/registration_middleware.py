from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.domain.ports.repositories import UserRepository
from src.application import EnsureUserExists


class RegistrationMiddleware(BaseMiddleware):
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data["user"] = await EnsureUserExists(
            self.user_repo, data["event_context"].chat.id
        ).execute()
        return await handler(event, data)
