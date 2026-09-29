from .base import SessionRelatedUseCase
from src.domain.models import Argue


class HandleResolution(SessionRelatedUseCase):
    async def execute(self, argue: Argue, resolution: str):
        await self.session.message_service.send_resolution(
            self.session.answer_message_context, resolution
        )
        argue.add_resolution(resolution)
        await self.session.context_service.set_processed(argue)
