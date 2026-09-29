import pytest

from src.application import ClearContext, SendInstructions
from src.domain.exceptions import UndefinedDefendant

from src.domain.models import Speaker
from tests.cases.base import BaseTestGroup


class TestCommands(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_clear_context(self, session, go_uc):
        await self.add_messages(session, 3)

        await session.context_service.set_defendant(Speaker("человек 0"))
        await go_uc.execute()

        await ClearContext(session).execute()
        assert (await session.context_service.get_processed()) is None
        with pytest.raises(UndefinedDefendant):
            await session.context_service.get_defendant()

    @pytest.mark.asyncio
    async def test_start(self, session, go_uc):
        await SendInstructions(session).execute()
        session.message_service.send_instructions.assert_awaited()
