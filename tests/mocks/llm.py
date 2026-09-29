from typing import Any, Dict
from unittest.mock import AsyncMock

from src.domain.models.llm_output import LLMOutput
from src.domain.ports import LanguageModelInterface


class MockLanguageModel(LanguageModelInterface):
    """Mock LanguageModel using AsyncMock for maximum flexibility"""

    def __init__(self):
        self._call_history = []
        self.generate = AsyncMock(side_effect=self._generate_impl)

    async def _generate_impl(
        self,
        payload: Dict[str, Any],
        is_function: bool = False,
        prefer_sync_api_call: bool = False,
    ) -> LLMOutput:
        """Implementation for generate method"""
        self._call_history.append(
            {
                "payload": payload,
                "is_function": is_function,
                "prefer_sync_api_call": prefer_sync_api_call,
            }
        )

        return LLMOutput(
            generated_output=f"Async mock response for: {payload}",
            full_response={"async_mock": True, "payload": payload},
            request_id=len(self._call_history),
        )

    # Configuration methods
    def set_return_value(self, llm_output: LLMOutput):
        """Set return value for generate calls"""
        self.generate.return_value = llm_output
        return self

    def set_side_effect(self, side_effect):
        """Set side effect for generate calls"""
        self.generate.side_effect = side_effect
        return self

    # Test helper methods
    def get_call_history(self):
        return self._call_history.copy()

    def get_last_call(self):
        return self._call_history[-1] if self._call_history else None
