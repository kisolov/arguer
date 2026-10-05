from config import AppConfig
from .base import SessionRelatedUseCase
from src.domain.models import Dialogue, UnprocessedMessage
from src.domain.operations import UnprocessedMessageFactory
from src.domain.exceptions import (
    ContextEmpty,
    ContextLimitExceeded,
    MessagesLimitExceeded,
    MediaLimitExceeded,
)
from ..session import Session


class AddMessageToUnprocessed(SessionRelatedUseCase):
    def __init__(self, session: Session, app_config: AppConfig):
        self.messages_limit = app_config.unprocessed_messages_limit
        self.media_limit_seconds = app_config.unprocessed_media_duration_limit
        self.context_symbols_limit = app_config.context_symbols_limit
        super().__init__(session)

    async def execute(self):
        unprocessed_message = await self._create_unprocessed()
        await self._add_to_unprocessed(unprocessed_message)

    async def _add_to_unprocessed(self, unprocessed_message):
        try:
            dialogue = await self.session.context_service.get_unprocessed()
        except ContextEmpty:
            dialogue = Dialogue()
        self._validate_addition(dialogue, unprocessed_message)
        await self._validate_context_size(dialogue, unprocessed_message)
        dialogue.add_message(unprocessed_message)
        await self.session.context_service.set_unprocessed(dialogue)

    async def _validate_context_size(
        self, dialogue: Dialogue, new_message: UnprocessedMessage
    ):
        """Вся история спора уходит в модель, у которой ограничен контекст.

        Голос ещё не распознан и не считается: его объём за раунд ограничен
        лимитом длительности.
        """
        history = await self.session.context_service.get_processed()
        total = (
            (history.total_symbols if history else 0)
            + dialogue.total_symbols
            + len(new_message.text or "")
        )
        if total > self.context_symbols_limit:
            raise ContextLimitExceeded(self.context_symbols_limit)

    async def _create_unprocessed(self):
        unprocessed_message = UnprocessedMessageFactory().create(
            self.session.event.forward_from_name,
            self.session.event.media,
            self.session.event.data,
        )
        return unprocessed_message

    def _validate_addition(self, dialogue: Dialogue, new_message: UnprocessedMessage):
        if len(dialogue.messages) >= self.messages_limit:
            raise MessagesLimitExceeded(self.messages_limit)
        if (
            new_message.media
            and dialogue.media_duration + new_message.media.duration
            > self.media_limit_seconds
        ):
            raise MediaLimitExceeded(self.media_limit_seconds)


class AddTestMessageToUnprocessed(AddMessageToUnprocessed):
    async def execute(self, sender_name: str, text_data: str, media=None):
        unprocessed_message = UnprocessedMessageFactory().create(
            speaker_name=sender_name,
            media=media,
            text=text_data,
        )
        await self._add_to_unprocessed(unprocessed_message)
