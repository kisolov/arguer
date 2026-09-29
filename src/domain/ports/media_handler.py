from abc import ABC, abstractmethod

from ..models import Media


class MediaHandler(ABC):
    @abstractmethod
    async def get_media_as_text(self, media: Media) -> str: ...
