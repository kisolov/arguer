import pytest

from src.application import AddMessageToUnprocessed
from src.application.uc.add_reasoning_to_unprocessed import AddTestMessageToUnprocessed
from src.domain.exceptions import MediaLimitExceeded, MessagesLimitExceeded
from src.domain.models import Media
from tests.cases.base import BaseTestGroup
from tests.utils.factories import EventContextFactory


class TestMessageIntake(BaseTestGroup):
    @pytest.fixture
    def app_config(self):
        return self.container.config.app_config()

    @pytest.mark.asyncio
    async def test_forwarded_text_is_stored_with_speaker(self, session, app_config):
        session.event = EventContextFactory(
            user=session.user, data="привет", forward_from_name="Аня"
        )

        await AddMessageToUnprocessed(session, app_config).execute()

        message = (await session.context_service.get_unprocessed()).messages[0]
        assert (message.speaker.name, message.text) == ("Аня", "привет")

    @pytest.mark.asyncio
    async def test_hidden_sender_falls_back_to_hidden(self, session, app_config):
        session.event = EventContextFactory(user=session.user, data="привет")

        await AddMessageToUnprocessed(session, app_config).execute()

        message = (await session.context_service.get_unprocessed()).messages[0]
        assert message.speaker.name == "hidden"

    @pytest.mark.asyncio
    async def test_event_without_text_and_media_is_rejected(self, session, app_config):
        session.event = EventContextFactory(user=session.user, data=None)

        with pytest.raises(ValueError):
            await AddMessageToUnprocessed(session, app_config).execute()

    @pytest.mark.asyncio
    async def test_messages_up_to_the_limit_are_accepted(self, session, app_config):
        await self.add_messages(session, app_config.unprocessed_messages_limit)

        dialogue = await session.context_service.get_unprocessed()
        assert len(dialogue.messages) == app_config.unprocessed_messages_limit

    @pytest.mark.asyncio
    async def test_media_total_exactly_at_limit_is_accepted(self, session, app_config):
        limit = app_config.unprocessed_media_duration_limit

        await self.add_messages(session, 2, media_duration=limit)

        assert (await session.context_service.get_unprocessed()).media_duration == limit

    @pytest.mark.asyncio
    async def test_rejected_message_is_not_stored(self, session, app_config):
        await self.add_messages(session, app_config.unprocessed_messages_limit)

        with pytest.raises(MessagesLimitExceeded):
            await self.add_messages(session, 1)

        dialogue = await session.context_service.get_unprocessed()
        assert len(dialogue.messages) == app_config.unprocessed_messages_limit


class TestTestMessageIntake(BaseTestGroup):
    @pytest.fixture
    def app_config(self):
        return self.container.config.app_config()

    @pytest.mark.asyncio
    async def test_adds_message_from_named_sender(self, session, app_config):
        await AddTestMessageToUnprocessed(session, app_config).execute(
            sender_name="User 7", text_data="привет"
        )

        message = (await session.context_service.get_unprocessed()).messages[0]
        assert (message.speaker.name, message.text) == ("User 7", "привет")

    @pytest.mark.asyncio
    async def test_respects_messages_limit(self, session, app_config):
        uc = AddTestMessageToUnprocessed(session, app_config)
        for _ in range(app_config.unprocessed_messages_limit):
            await uc.execute(sender_name="User 1", text_data="x")

        with pytest.raises(MessagesLimitExceeded):
            await uc.execute(sender_name="User 1", text_data="x")

    @pytest.mark.asyncio
    async def test_respects_media_limit(self, session, app_config):
        too_long = Media("v.ogg", app_config.unprocessed_media_duration_limit + 1)

        with pytest.raises(MediaLimitExceeded):
            await AddTestMessageToUnprocessed(session, app_config).execute(
                sender_name="User 1", text_data="x", media=too_long
            )
