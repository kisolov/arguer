from typing import List, Dict

from src.domain.models import Argue
from src.domain.ports import LanguageModelInterface
from src.domain.models.llm_output import LLMOutput


class LLMDisputeResolver:
    def __init__(self, llm: LanguageModelInterface, base_prompt: str):
        self.llm = llm
        self.base_prompt = base_prompt

    async def resolve(self, argue: Argue) -> LLMOutput:
        prompt_payload = self._build_prompt_payload(argue)

        return await self.llm.generate(
            {
                "messages": [
                    {"role": "system", "content": self.base_prompt},
                    {
                        "role": "assistant",
                        "content": f"Я готов отстаивать вашу позицию любыми способами. Пришлите мне диалог.",
                    },
                    *prompt_payload,
                ]
            },
            prefer_sync_api_call=True,
        )

    def _build_prompt_payload(self, argue: Argue):
        prompt_payload: List[Dict[str, str]] = []
        argue_str: str = ""

        for reasoning in argue.reasoning_list:
            if reasoning.speaker == argue.defendant:
                argue_str += f"клиент - {reasoning.content} - ЗАЩИТИТЬ\n"
            elif reasoning.speaker == "assistant":
                prompt_payload.append({"role": "user", "content": argue_str})
                prompt_payload.append(
                    {"role": "assistant", "content": reasoning.content}
                )
                argue_str = ""
                continue
            else:
                argue_str += f"оппонент - {reasoning.content} - ОПРОВЕРГНУТЬ\n"

        prompt_payload.append({"role": "user", "content": argue_str})
        return prompt_payload
