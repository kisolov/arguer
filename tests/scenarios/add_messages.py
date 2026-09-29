import math

from config import AppConfig
from src.application import AddMessageToUnprocessed, Session
from src.application.uc.base import SessionRelatedUseCase
from src.domain.models import Media
from tests.utils.factories import EventContextFactory


class AddMessages(SessionRelatedUseCase):
    def __init__(self, session: Session, app_config: AppConfig):
        self.app_config = app_config
        super().__init__(session)

    async def execute(self, messages_count: int = 9, media_duration: int = 0):
        media = None
        if media_duration:
            media = Media(
                url="test.com", duration=math.ceil(media_duration / messages_count)
            )
        for i in range(messages_count):
            self.session.event = EventContextFactory(
                user=self.session.event.user,
                data=f"сообщение {i}",
                forward_from_name=f"человек {i % 2}",
                media=media,
            )
            await AddMessageToUnprocessed(self.session, self.app_config).execute()
