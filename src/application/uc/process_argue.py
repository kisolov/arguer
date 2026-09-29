from logs import logger
from src.domain.exceptions import LanguageModelError, UnexpectedError
from src.domain.models import Argue
from src.domain.operations import LLMDisputeResolver
from .base import AsyncUseCase


class ProcessArgue(AsyncUseCase):
    def __init__(self, dispute_resolver: LLMDisputeResolver, argue: Argue):
        self.dispute_resolver = dispute_resolver
        self.argue = argue

    async def execute(self) -> str:
        try:
            return await self.dispute_resolver.resolve(self.argue)
        except LanguageModelError:
            logger.error("Сбой языковой модели", exc_info=True)
            raise UnexpectedError()
