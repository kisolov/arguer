from .base import SessionRelatedUseCase
from src.domain.exceptions import ContextEmpty


class FetchDialogue(SessionRelatedUseCase):
    async def execute(self):
        return await self.session.context_service.get_unprocessed()
