from .base import SessionRelatedUseCase
from src.domain.exceptions import UnexpectedError
from src.domain.models import Argue
from src.domain.models.llm_output import LLMOutput


class HandleResolution(SessionRelatedUseCase):
    async def execute(self, argue: Argue, resolution: LLMOutput):
        if resolution.success:
            await self.session.message_service.send_resolution(
                self.session.answer_message_context, resolution
            )
            argue.add_resolution(resolution)
            await self.session.context_service.set_processed(argue)

        else:
            raise UnexpectedError()
