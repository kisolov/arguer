from .base import SessionRelatedUseCase
from ...domain.exceptions import ContextEmpty


class ShowContextInfo(SessionRelatedUseCase):
    async def execute(self):
        symbols = 0
        media_duration = 0

        try:
            unprocessed = await self.session.context_service.get_unprocessed()
            symbols += unprocessed.total_symbols
            media_duration += unprocessed.media_duration
        except ContextEmpty:
            pass

        processed = await self.session.context_service.get_processed()

        if processed:
            symbols += processed.total_symbols

        await self.session.message_service.send_context_info(
            self.session.answer_message_context, symbols, media_duration
        )
