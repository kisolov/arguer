from .base import SessionRelatedUseCase
from src.domain.models import MessageContext


class SendInstructions(SessionRelatedUseCase):
    async def execute(self):
        await self.session.message_service.send_instructions(
            MessageContext(self.session.event.user)
        )
