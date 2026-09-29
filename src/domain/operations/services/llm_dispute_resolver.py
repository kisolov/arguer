from typing import List

from src.domain.models import Argue, ChatMessage, Speaker
from src.domain.ports import LanguageModelInterface

ASSISTANT_GREETING = (
    "Я готов отстаивать вашу позицию любыми способами. Пришлите мне диалог."
)


class LLMDisputeResolver:
    def __init__(self, llm: LanguageModelInterface, base_prompt: str):
        self.llm = llm
        self.base_prompt = base_prompt

    async def resolve(self, argue: Argue) -> str:
        return await self.llm.complete(
            [
                ChatMessage("system", self.base_prompt),
                ChatMessage("assistant", ASSISTANT_GREETING),
                *self._build_dialogue(argue),
            ]
        )

    def _build_dialogue(self, argue: Argue) -> List[ChatMessage]:
        dialogue: List[ChatMessage] = []
        argue_str: str = ""

        for reasoning in argue.reasoning_list:
            if reasoning.speaker == argue.defendant:
                argue_str += f"клиент - {reasoning.content} - ЗАЩИТИТЬ\n"
            elif reasoning.speaker == Speaker("assistant"):
                dialogue.append(ChatMessage("user", argue_str))
                dialogue.append(ChatMessage("assistant", reasoning.content))
                argue_str = ""
            else:
                argue_str += f"оппонент - {reasoning.content} - ОПРОВЕРГНУТЬ\n"

        dialogue.append(ChatMessage("user", argue_str))
        return dialogue
