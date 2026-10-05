import pytest

from src.application import SelectDefendant, SendDefendantSelection
from src.application.uc.fetch_defendant import FetchDefendant
from src.application.uc.fetch_dialogue import FetchDialogue
from src.domain.exceptions import ContextEmpty, UndefinedDefendant, UnknownDefendant
from src.domain.models import Dialogue, Speaker, UnprocessedMessage
from src.infrastructure import Callbacks
from tests.cases.base import BaseTestGroup
from tests.utils.factories import EventContextFactory


class TestDefendantSelection(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_selection_menu_lists_participants_and_waits_for_choice(
        self, session
    ):
        await self.add_messages(session, 4)

        await SendDefendantSelection(session).execute()

        assert session.context_service._current_state == "defendant_selection"
        _, variants = session.message_service.send_defendant_selection.await_args.args
        assert sorted(v.name for v in variants) == ["человек 0", "человек 1"]

    @pytest.mark.asyncio
    async def test_selection_menu_requires_context(self, session):
        with pytest.raises(ContextEmpty):
            await SendDefendantSelection(session).execute()

    def press(self, session, index):
        session.event = EventContextFactory(
            user=session.user,
            data=Callbacks.DefendantSelectionCallback(defendant_index=index),
        )

    @pytest.mark.asyncio
    async def test_choice_sets_defendant_and_leaves_selection_state(self, session):
        await self.add_messages(session, 4)
        await SendDefendantSelection(session).execute()
        self.press(session, 1)

        await SelectDefendant(session).execute()

        assert await session.context_service.get_defendant() == Speaker("человек 1")
        assert session.context_service._current_state is None
        assert len(session.message_service.get_deleted_messages()) == 1

    @pytest.mark.asyncio
    async def test_button_keeps_meaning_after_new_participant_appears(self, session):
        await self.add_messages(session, 4)
        await SendDefendantSelection(session).execute()
        _, offered = session.message_service.send_defendant_selection.await_args.args
        # Пока меню открыто, пришла пересылка от участника, чьё имя встанет первым
        await self.forward(session, "Аааа", "новое сообщение")
        self.press(session, 1)

        await SelectDefendant(session).execute()

        assert await session.context_service.get_defendant() == offered[1]

    @pytest.mark.asyncio
    async def test_choice_outside_menu_is_rejected(self, session):
        await self.add_messages(session, 4)
        await SendDefendantSelection(session).execute()
        self.press(session, 7)

        with pytest.raises(UnknownDefendant):
            await SelectDefendant(session).execute()

        with pytest.raises(UndefinedDefendant):
            await session.context_service.get_defendant()

    @pytest.mark.asyncio
    async def test_choice_without_menu_is_rejected(self, session):
        await self.add_messages(session, 4)
        self.press(session, 0)

        with pytest.raises(UnknownDefendant):
            await SelectDefendant(session).execute()

    @pytest.mark.asyncio
    async def test_participant_gone_after_clear_is_rejected(self, session):
        await self.add_messages(session, 4)
        await SendDefendantSelection(session).execute()
        await session.context_service.set_unprocessed(Dialogue())
        await self.forward(session, "кто-то другой", "привет")
        self.press(session, 0)

        with pytest.raises(UnknownDefendant):
            await SelectDefendant(session).execute()

    async def forward(self, session, speaker, text):
        dialogue = await session.context_service.get_unprocessed()
        dialogue.add_message(UnprocessedMessage(Speaker(speaker), text=text))
        await session.context_service.set_unprocessed(dialogue)


class TestFetchers(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_fetch_dialogue_without_messages_raises(self, session):
        with pytest.raises(ContextEmpty):
            await FetchDialogue(session).execute()

    @pytest.mark.asyncio
    async def test_fetch_dialogue_returns_collected_messages(self, session):
        await self.add_messages(session, 3)

        assert len((await FetchDialogue(session).execute()).messages) == 3

    @pytest.mark.asyncio
    async def test_fetch_defendant_without_choice_raises(self, session):
        with pytest.raises(UndefinedDefendant):
            await FetchDefendant(session).execute()

    @pytest.mark.asyncio
    async def test_fetch_defendant_returns_choice(self, session):
        await session.context_service.set_defendant(Speaker("a"))

        assert await FetchDefendant(session).execute() == Speaker("a")
