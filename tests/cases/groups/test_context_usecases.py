import pytest

from src.application.uc.handle_resolution import HandleResolution
from src.application.uc.process_unprocessed import ProcessUnprocessed
from src.application.uc.send_context_info import ShowContextInfo
from src.domain.exceptions import ContextEmpty
from src.domain.models import Argue, Reasoning, Speaker
from tests.cases.base import BaseTestGroup


class TestShowContextInfo(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_empty_context_reports_zeroes(self, session):
        await ShowContextInfo(session).execute()

        _, symbols, media = session.message_service.send_context_info.await_args.args
        assert (symbols, media) == (0, 0)

    @pytest.mark.asyncio
    async def test_counts_unprocessed_and_processed_symbols(self, session):
        await self.add_messages(session, 2, media_duration=10)
        unprocessed = await session.context_service.get_unprocessed()
        await session.context_service.set_processed(
            Argue([Reasoning("12345", Speaker("a"))], Speaker("a"))
        )

        await ShowContextInfo(session).execute()

        _, symbols, media = session.message_service.send_context_info.await_args.args
        assert symbols == unprocessed.total_symbols + 5
        assert media == 10


class TestProcessUnprocessed(BaseTestGroup):
    @pytest.fixture
    def process(self, session):
        return ProcessUnprocessed(session, self.container.core.argue_service())

    @pytest.mark.asyncio
    async def test_turns_unprocessed_into_argue_and_clears_them(self, session, process):
        await self.add_messages(session, 3)
        await session.context_service.set_defendant(Speaker("человек 0"))

        argue = await process.execute()

        assert [r.content for r in argue.reasoning_list] == [
            "сообщение 0",
            "сообщение 1",
            "сообщение 2",
        ]
        with pytest.raises(ContextEmpty):
            await session.context_service.get_unprocessed()
        assert await session.context_service.get_processed() is argue
        assert await session.context_service.get_defendant() == Speaker("человек 0")

    @pytest.mark.asyncio
    async def test_appends_to_previously_processed_argue(self, session, process):
        await self.add_messages(session, 1)
        await session.context_service.set_defendant(Speaker("человек 0"))
        await session.context_service.set_processed(
            Argue([Reasoning("раньше", Speaker("человек 0"))], Speaker("человек 0"))
        )

        argue = await process.execute()

        assert [r.content for r in argue.reasoning_list] == ["раньше", "сообщение 0"]


class TestHandleResolution(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_sends_resolution_and_stores_it_as_assistant_turn(self, session):
        argue = Argue([Reasoning("тезис", Speaker("a"))], Speaker("a"))

        await HandleResolution(session).execute(argue, "итог")

        _, text = session.message_service.send_resolution.await_args.args
        assert text == "итог"
        stored = await session.context_service.get_processed()
        assert stored.reasoning_list[-1] == Reasoning("итог", Speaker("assistant"))
