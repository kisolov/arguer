import pytest

from src.domain.exceptions import LanguageModelError, UnexpectedError
from src.domain.models import Speaker
from tests.cases.base import BaseTestGroup


class TestLanguageModelFailure(BaseTestGroup):
    @pytest.fixture
    def llm(self):
        llm = self.container.interfaces.llm()
        llm.reset()
        yield llm
        llm.reset()

    @pytest.mark.asyncio
    async def test_go_maps_model_failure_to_unexpected_error(
        self, session, go_uc, llm
    ):
        await self.add_messages(session)
        await session.context_service.set_defendant(Speaker("человек 0"))
        llm.set_side_effect(LanguageModelError("down"))

        with pytest.raises(UnexpectedError):
            await go_uc.execute()

        session.message_service.send_resolution.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_go_removes_progress_message_when_model_fails(
        self, session, go_uc, llm
    ):
        await self.add_messages(session)
        await session.context_service.set_defendant(Speaker("человек 0"))
        llm.set_side_effect(LanguageModelError("down"))

        with pytest.raises(UnexpectedError):
            await go_uc.execute()

        session.message_service.send_progress_message.assert_awaited()
        session.message_service.delete_message.assert_awaited()
