from .base import SessionRelatedUseCase


class FetchDefendant(SessionRelatedUseCase):
    async def execute(self):
        return await self.session.context_service.get_defendant()
