from logs import logger
from src.domain.models import (
    Argue,
)
from src.domain.operations import LLMDisputeResolver
from .base import AsyncUseCase


class ProcessArgue(AsyncUseCase):
    def __init__(self, dispute_resolver: LLMDisputeResolver, argue: Argue):
        self.dispute_resolver = dispute_resolver
        self.argue = argue

    async def execute(self):
        logger.info(f"Начало обработки: {self.argue}")
        resolution = await self.dispute_resolver.resolve(self.argue)
        logger.info(f"Результат: {resolution}")
        return resolution
