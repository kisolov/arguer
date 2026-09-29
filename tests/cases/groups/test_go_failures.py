import pytest

from src.domain.exceptions import ContextEmpty, InsufficientFunds
from src.domain.models import Speaker
from tests.cases.base import BaseTestGroup


class TestGoFailures(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_without_messages_fails_before_charging(self, session, go_uc):
        with pytest.raises(ContextEmpty):
            await go_uc.execute()

        assert session.user.bal == 1000

    @pytest.mark.asyncio
    async def test_insufficient_funds_stops_before_processing(self, session, go_uc):
        session.user.bal = 1
        await self.add_messages(session, 3)
        await session.context_service.set_defendant(Speaker("человек 0"))

        with pytest.raises(InsufficientFunds):
            await go_uc.execute()

        session.message_service.send_progress_message.assert_not_awaited()
        assert len((await session.context_service.get_unprocessed()).messages) == 3
        assert session.context_service._current_state is None

    @pytest.mark.asyncio
    async def test_state_is_cleared_after_success(self, session, go_uc):
        await self.add_messages(session, 3)
        await session.context_service.set_defendant(Speaker("человек 0"))

        await go_uc.execute()

        assert session.context_service._current_state is None
