from typing import Protocol, Sequence

from src.domain.models.chat_message import ChatMessage


class LanguageModelInterface(Protocol):
    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        """Возвращает текст ответа модели. При сбое бросает LanguageModelError."""
        ...
