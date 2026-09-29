from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.domain.models import EventTypes, PopupContext
from src.domain.models.event_ctx import EventContext
from src.application import Session
from src.infrastructure import AiogramMessageService, AiogramContextService
from src.infrastructure.aiogram.popup_service import AiogramPopupService


class SessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: EventContext,
        data: Dict[str, Any],
    ) -> Any:
        context_service = AiogramContextService(data["state"])
        message_service = AiogramMessageService(data["bot"])
        popup_service = (
            AiogramPopupService(data["bot"], PopupContext(event.event_id))
            if event.event_type == EventTypes.BUTTON_PRESSED
            else None
        )

        session = Session(event, context_service, message_service, popup_service)
        return await handler(session, {})
