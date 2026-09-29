from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware, types
from aiogram.filters.callback_data import CallbackData
from aiogram.types import TelegramObject

from src.domain.models import Media, EventContext, EventTypes


class MappingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        media = None
        forward_from_name = None

        if isinstance(event, types.Message):
            event_data = event.text or event.caption
            event_message_id = event.message_id
            event_type = EventTypes.INCOMING_MESSAGE
            event_id = event_message_id
            media = event.voice or event.video_note
            bot = data["bot"]

            if media:
                file_id = media.file_id
                file = await bot.get_file(file_id)
                url = bot.session.api.file_url(bot.token, file.file_path)
                media = Media(url, media.duration)

            if event.forward_from:
                forward_from_name = getattr(event.forward_from, "full_name", "hidden")
            elif event.forward_sender_name:
                forward_from_name = event.forward_sender_name

        elif isinstance(event, types.CallbackQuery):
            callback_data: CallbackData | None = data.get("callback_data", None)
            event_data = callback_data or event.data
            event_message_id = event.message.message_id
            event_type = EventTypes.BUTTON_PRESSED
            event_id = event.id

        else:
            raise ValueError("Unknown event type")

        event_ctx = EventContext(
            event_message_id=event_message_id,
            data=event_data,
            user=data["user"],
            event_type=event_type,
            event_id=event_id,
            media=media,
            forward_from_name=forward_from_name,
        )
        return await handler(event_ctx, data)
