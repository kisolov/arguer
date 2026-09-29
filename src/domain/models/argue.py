from dataclasses import dataclass
from typing import List

from .reasoning import Reasoning
from .speaker import Speaker
from .llm_output import LLMOutput


@dataclass
class Argue:
    reasoning_list: List[Reasoning]
    defendant: Speaker

    def __add__(self, other):
        if isinstance(other, Argue):
            return Argue(self.reasoning_list + other.reasoning_list, self.defendant)
        raise NotImplemented()

    @property
    def total_symbols(self):
        return sum(len(r.content) for r in self.reasoning_list)

    def add_reasoning(self, reasoning: Reasoning):
        self.reasoning_list.append(reasoning)

    def add_resolution(self, resolution: LLMOutput):
        self.add_reasoning(Reasoning(resolution.generated_output, Speaker("assistant")))
