from unittest.mock import AsyncMock, Mock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from src.domain.models import BuyOption, MessageContext, PopupContext, Speaker, User
from src.domain.ports import Texts
from src.infrastructure import (
    AiogramContextService,
    AiogramMessageService,
    Callbacks,
    States,
)
from src.infrastructure.aiogram.message_service import Keyboards
from src.infrastructure.aiogram.popup_service import AiogramPopupService
from tests.cases.base import BaseTestGroup

USER = User(telegram_id=555, id=1, bal=12.5)


class TestAiogramMessageService(BaseTestGroup):
    @pytest.fixture
    def bot(self):
        bot = Mock()
        bot.send_message = AsyncMock(return_value=Mock(message_id=321))
        bot.edit_message_text = AsyncMock()
        bot.delete_message = AsyncMock()
        return bot

    @pytest.fixture
    def service(self, bot):
        return AiogramMessageService(bot)

    @pytest.mark.asyncio
    async def test_new_message_is_sent_and_its_id_returned(self, service, bot):
        ctx = await service.send_progress_message(MessageContext(USER))

        bot.send_message.assert_awaited_once_with(
            chat_id=555, text=Texts.PROGRESS_MESSAGE, reply_markup=None
        )
        assert ctx.message_id == 321

    @pytest.mark.asyncio
    async def test_known_message_is_edited_in_place(self, service, bot):
        ctx = await service.send_context_info(MessageContext(USER, 7), 10, 2)

        bot.send_message.assert_not_awaited()
        assert bot.edit_message_text.await_args.kwargs["message_id"] == 7
        assert "10 символов, 2 секунд" in bot.edit_message_text.await_args.args[0]
        assert ctx.message_id == 7

    @pytest.mark.asyncio
    async def test_delete_message(self, service, bot):
        await service.delete_message(MessageContext(USER, 7))

        bot.delete_message.assert_awaited_once_with(555, 7)

    @pytest.mark.asyncio
    async def test_balance_menu_shows_balance_formula_and_buttons(self, service, bot):
        await service.send_balance_menu(MessageContext(USER), "ФОРМУЛА")

        kwargs = bot.send_message.await_args.kwargs
        assert "12.50✨" in kwargs["text"] and "ФОРМУЛА" in kwargs["text"]
        buttons = kwargs["reply_markup"].inline_keyboard[0]
        assert [b.callback_data for b in buttons] == ["update", "top_up"]

    @pytest.mark.asyncio
    async def test_defendant_selection_has_button_per_speaker(self, service, bot):
        await service.send_defendant_selection(
            MessageContext(USER), [Speaker("Аня"), Speaker("Боря")]
        )

        rows = bot.send_message.await_args.kwargs["reply_markup"].inline_keyboard
        assert [row[0].text for row in rows] == ["Аня", "Боря"]
        packed = rows[0][0].callback_data
        assert Callbacks.DefendantSelectionCallback.unpack(packed).defendant_name == "Аня"

    @pytest.mark.asyncio
    async def test_prices_menu_lists_options_with_back_button(self, service, bot):
        options = [BuyOption(100, 20, "100✨"), BuyOption(500, 80, "500✨")]

        await service.send_prices_menu(MessageContext(USER), options)

        rows = bot.send_message.await_args.kwargs["reply_markup"].inline_keyboard
        assert [row[0].text for row in rows] == [
            "100✨ за 20₽",
            "500✨ за 80₽",
            "Назад",
        ]
        assert Callbacks.BuyOptionSelectionCallback.unpack(
            rows[1][0].callback_data
        ).option_index == 1
        assert rows[2][0].callback_data == "buy_options_back"

    def test_callback_payload_fits_telegram_limit(self):
        packed = Keyboards.defendant_selection([Speaker("а" * 20)])
        assert len(packed.inline_keyboard[0][0].callback_data.encode()) <= 64


class TestAiogramContextService(BaseTestGroup):
    @pytest.fixture
    def context(self):
        fsm = FSMContext(
            MemoryStorage(), StorageKey(bot_id=1, chat_id=1, user_id=1)
        )
        return AiogramContextService(fsm)

    @pytest.mark.asyncio
    async def test_values_roundtrip(self, context):
        await context.set_defendant(Speaker("a"))

        assert await context.get_defendant() == Speaker("a")

    @pytest.mark.asyncio
    async def test_missing_key_raises_key_error(self, context):
        with pytest.raises(KeyError):
            await context.get("nothing")

    @pytest.mark.asyncio
    async def test_update_keeps_other_keys_but_set_replaces_all(self, context):
        await context.update({"a": 1})
        await context.update({"b": 2})
        assert (await context.get("a"), await context.get("b")) == (1, 2)

        await context.set({"c": 3})
        with pytest.raises(KeyError):
            await context.get("a")
        assert await context.get("c") == 3

    @pytest.mark.asyncio
    async def test_clear_data_drops_everything(self, context):
        await context.update({"a": 1})

        await context.clear_data()

        with pytest.raises(KeyError):
            await context.get("a")

    @pytest.mark.asyncio
    async def test_states_are_set_and_cleared(self, context):
        await context.set_processing_state()
        assert await context.fsm.get_state() == States.processing.state

        await context.set_defendant_selection_state()
        assert await context.fsm.get_state() == States.defendant_selection.state

        await context.clear_state()
        assert await context.fsm.get_state() is None


class TestAiogramPopupService(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_updated_popup_answers_callback_query(self):
        bot = Mock(answer_callback_query=AsyncMock())

        await AiogramPopupService(bot, PopupContext("cq-1")).notify_updated()

        bot.answer_callback_query.assert_awaited_once_with("cq-1", "Обновлено", False)
