from typing import Sequence
from unittest.mock import AsyncMock

from src.domain.models import ChatMessage
from src.domain.ports import LanguageModelInterface


class MockLanguageModel(LanguageModelInterface):
    """Mock LanguageModel using AsyncMock for maximum flexibility"""

    def __init__(self):
        self._call_history = []
        self.complete = AsyncMock(side_effect=self._complete_impl)

    async def _complete_impl(self, messages: Sequence[ChatMessage]) -> str:
        self._call_history.append(list(messages))
        return f"Async mock response for: {len(messages)} messages"

    # Configuration methods
    def set_return_value(self, text: str):
        """Set return value for complete calls"""
        self.complete.side_effect = None
        self.complete.return_value = text
        return self

    def set_side_effect(self, side_effect):
        """Set side effect for complete calls"""
        self.complete.side_effect = side_effect
        return self

    def reset(self):
        """Back to default behaviour, forget recorded calls"""
        self.complete.reset_mock(return_value=True, side_effect=True)
        self.complete.side_effect = self._complete_impl
        self._call_history.clear()

    # Test helper methods
    def get_call_history(self):
        return self._call_history.copy()

    def get_last_call(self):
        return self._call_history[-1] if self._call_history else None
