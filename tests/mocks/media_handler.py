from src.domain.models import Media
from src.domain.ports import MediaHandler


class MockMediaHandler(MediaHandler):
    async def get_media_as_text(self, media: Media) -> str:
        return "Текст из медиа"
