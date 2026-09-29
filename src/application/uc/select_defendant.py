from .base import SessionRelatedUseCase
from src.domain.models import MessageContext, Speaker


class SelectDefendant(SessionRelatedUseCase):
    async def execute(self):
        assert self.session.event.data.defendant_name in [
            p.name
            for p in (await self.session.context_service.get_unprocessed()).partipitians
        ]
        await self.session.message_service.delete_message(
            MessageContext(self.session.user, self.session.event.event_message_id)
        )
        await self.session.context_service.set_defendant(
            Speaker(self.session.event.data.defendant_name)
        )
        await self.session.context_service.clear_state()
