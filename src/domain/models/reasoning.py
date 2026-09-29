from dataclasses import dataclass

from src.domain.models.speaker import Speaker


@dataclass
class Reasoning:
    content: str
    speaker: Speaker
