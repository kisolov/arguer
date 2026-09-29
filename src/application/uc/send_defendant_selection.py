from .base import SessionRelatedUseCase


class SendDefendantSelection(SessionRelatedUseCase):
    async def execute(self):
        speakers = (await self.session.context_service.get_unprocessed()).partipitians

        await self.session.context_service.set_defendant_selection_state()

        await self.session.message_service.send_defendant_selection(
            self.session.answer_message_context, speakers
        )
