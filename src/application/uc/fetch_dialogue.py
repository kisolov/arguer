from .base import SessionRelatedUseCase


class FetchDialogue(SessionRelatedUseCase):
    async def execute(self):
        return await self.session.context_service.get_unprocessed()
