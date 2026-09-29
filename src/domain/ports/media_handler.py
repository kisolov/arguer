from abc import ABC, abstractmethod

from .speech_recognition import SpeechRecognitionInterface
from ..models import Media


class MediaHandler(ABC):
    @abstractmethod
    async def get_media_as_text(self, media: Media) -> str: ...
