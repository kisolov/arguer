from src.domain.operations import ArgueService
from .base import SessionRelatedUseCase
from ..session import Session


class ProcessUnprocessed(SessionRelatedUseCase):
    def __init__(self, session: Session, argue_service: ArgueService):
        super().__init__(session)
        self.argue_service = argue_service

    async def execute(self):
        dialogue = await self.session.context_service.get_unprocessed()
        defendant = await self.session.context_service.get_defendant()
        processed_before = await self.session.context_service.get_processed()

        argue = await self.argue_service.create_from_dialogue(dialogue, defendant)

        await self.session.context_service.clear_data()

        if processed_before:
            argue = processed_before + argue

        await self.session.context_service.set_processed(argue)
        await self.session.context_service.set_defendant(defendant)

        return argue
