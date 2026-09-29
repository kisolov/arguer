from typing import Protocol, Any, Dict

from src.domain.models.llm_output import LLMOutput


class LanguageModelInterface(Protocol):
    async def generate(
        self,
        payload: Dict[str, Any],
        is_function: bool = False,
        prefer_sync_api_call: bool = False,
    ) -> LLMOutput: ...
