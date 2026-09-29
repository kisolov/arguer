from .base import SessionRelatedUseCase


class ClearContext(SessionRelatedUseCase):
    async def execute(self):
        await self.session.context_service.clear_data()
        await self.session.context_service.clear_state()
        await self.session.message_service.notify_context_clean(
            self.session.answer_message_context
        )
