import pytest

from src.application import AddMessageToUnprocessed, ClearContext
from src.domain.exceptions import (
    UndefinedDefendant,
    ContextEmpty,
    MessagesLimitExceeded,
    MediaLimitExceeded,
)
from src.domain.models import Speaker
from tests.cases.base import BaseTestGroup

from tests.utils.factories import EventContextFactory


class TestMainScenario(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_go_raises_without_defendant(self, session, go_uc):
        await self.add_messages(session)
        with pytest.raises(UndefinedDefendant):
            await go_uc.execute()

    @pytest.mark.asyncio
    async def test_go_executes_with_defendant(self, session, go_uc):
        await self.add_messages(session)

        await session.context_service.set_defendant(Speaker("человек 0"))
        await go_uc.execute()

        assert len((await session.context_service.get_processed()).reasoning_list) == 10
        with pytest.raises(ContextEmpty):
            await session.context_service.get_unprocessed()

        session.message_service.send_progress_message.assert_awaited()
        session.message_service.send_resolution.assert_awaited()
        session.message_service.send_context_info.assert_awaited()

    @pytest.mark.asyncio
    async def test_go_adds_new_message_after_resolution(self, session, go_uc):
        await self.add_messages(session)

        await session.context_service.set_defendant(Speaker("человек 0"))
        await go_uc.execute()

        session.event = EventContextFactory(
            user=session.event.user, data="сообщение 9", forward_from_name="человек 1"
        )
        await AddMessageToUnprocessed(
            session, self.container.config.app_config()
        ).execute()
        assert len((await session.context_service.get_unprocessed()).messages) == 1

        await go_uc.execute()
        assert len((await session.context_service.get_processed()).reasoning_list) == 12

    @pytest.mark.asyncio
    async def test_go_message_limit_validation(self, session):
        messages_limit = self.container.config.app_config().unprocessed_messages_limit

        with pytest.raises(MessagesLimitExceeded):
            await self.add_messages(session, messages_limit + 1)

    @pytest.mark.asyncio
    async def test_go_media_limit_validation(self, session):
        media_limit = (
            self.container.config.app_config().unprocessed_media_duration_limit
        )
        with pytest.raises(MediaLimitExceeded):
            await self.add_messages(session, media_duration=media_limit + 10)

    @pytest.mark.asyncio
    async def test_usage_charge(self, session, go_uc):
        initial_balance = session.user.bal
        await self.add_messages(session)
        await session.context_service.set_defendant(Speaker("человек 0"))
        await go_uc.execute()

        assert session.user.bal < initial_balance
