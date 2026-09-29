from dataclasses import dataclass
from typing import Optional

from .media import Media
from .speaker import Speaker

@dataclass
class UnprocessedMessage:
    speaker: Speaker
    text: Optional[str] = None
    media: Optional[Media] = None

