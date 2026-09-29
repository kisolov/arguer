from unittest.mock import AsyncMock, Mock

import pytest
from aiogram import types

from src.application import Session
from src.domain.exceptions import ContextEmpty, InsufficientFunds
from src.domain.models import EventTypes, User
from src.infrastructure import (
    AiogramContextService,
    AiogramMessageService,
    Callbacks,
)
from src.infrastructure.aiogram.popup_service import AiogramPopupService
from src.presentation.aiogram.error_handling import ErrorHandlingMiddleware
from src.presentation.aiogram.mapping_middleware import MappingMiddleware
from src.presentation.aiogram.registration_middleware import RegistrationMiddleware
from src.presentation.aiogram.session_middleware import SessionMiddleware
from tests.cases.base import BaseTestGroup
from tests.utils.factories import EventContextFactory


def message(text="привет", **attrs):
    msg = Mock(spec=types.Message)
    msg.text = text
    msg.caption = None
    msg.message_id = 10
    msg.voice = None
    msg.video_note = None
    msg.forward_from = None
    msg.forward_sender_name = None
    for name, value in attrs.items():
        setattr(msg, name, value)
    return msg


class TestMappingMiddleware(BaseTestGroup):
    @pytest.fixture
    def user(self):
        return User(telegram_id=1, id=1)

    async def map(self, event, user, **data):
        handler = AsyncMock()
        data = {"user": user, "bot": Mock(), **data}
        await MappingMiddleware()(handler, event, data)
        return handler.await_args.args[0]

    @pytest.mark.asyncio
    async def test_plain_message(self, user):
        ctx = await self.map(message(), user)

        assert ctx.event_type is EventTypes.INCOMING_MESSAGE
        assert (ctx.data, ctx.event_message_id, ctx.user) == ("привет", 10, user)
        assert ctx.forward_from_name is None and ctx.media is None

    @pytest.mark.asyncio
    async def test_caption_is_used_when_text_is_missing(self, user):
        ctx = await self.map(message(text=None, caption="подпись"), user)

        assert ctx.data == "подпись"

    @pytest.mark.asyncio
    async def test_forward_from_user_uses_full_name(self, user):
        sender = Mock(full_name="Аня Иванова")

        ctx = await self.map(message(forward_from=sender), user)

        assert ctx.forward_from_name == "Аня Иванова"

    @pytest.mark.asyncio
    async def test_forward_from_hidden_user_uses_sender_name(self, user):
        ctx = await self.map(message(forward_sender_name="Скрытый"), user)

        assert ctx.forward_from_name == "Скрытый"

    @pytest.mark.asyncio
    async def test_voice_is_resolved_to_download_url(self, user):
        bot = Mock()
        bot.token = "TOKEN"
        bot.get_file = AsyncMock(return_value=Mock(file_path="voice/1.oga"))
        bot.session.api.file_url.return_value = "https://files/voice/1.oga"
        voice = Mock(file_id="f1", duration=4)

        ctx = await self.map(message(text=None, voice=voice), user, bot=bot)

        bot.get_file.assert_awaited_once_with("f1")
        bot.session.api.file_url.assert_called_once_with("TOKEN", "voice/1.oga")
        assert (ctx.media.url, ctx.media.duration) == ("https://files/voice/1.oga", 4)

    @pytest.mark.asyncio
    async def test_callback_query_carries_parsed_callback_data(self, user):
        query = Mock(spec=types.CallbackQuery)
        query.id = "cq-1"
        query.data = "raw"
        query.message = Mock(message_id=33)
        parsed = Callbacks.BuyOptionSelectionCallback(option_index=2)

        ctx = await self.map(query, user, callback_data=parsed)

        assert ctx.event_type is EventTypes.BUTTON_PRESSED
        assert (ctx.data, ctx.event_id, ctx.event_message_id) == (parsed, "cq-1", 33)

    @pytest.mark.asyncio
    async def test_callback_query_falls_back_to_raw_data(self, user):
        query = Mock(spec=types.CallbackQuery)
        query.id = "cq-1"
        query.data = "top_up"
        query.message = Mock(message_id=33)

        ctx = await self.map(query, user)

        assert ctx.data == "top_up"

    @pytest.mark.asyncio
    async def test_unknown_event_type_is_rejected(self, user):
        with pytest.raises(ValueError):
            await self.map(Mock(), user)


class TestRegistrationMiddleware(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_puts_registered_user_into_handler_data(self):
        users = self.container.interfaces.user_repository()
        handler = AsyncMock(return_value="ok")
        data = {"event_context": Mock(chat=Mock(id=7001))}

        result = await RegistrationMiddleware(users)(handler, Mock(), data)

        assert result == "ok"
        assert data["user"].telegram_id == 7001
        assert data["user"].id is not None


class TestSessionMiddleware(BaseTestGroup):
    async def build(self, event):
        handler = AsyncMock()
        data = {"state": Mock(), "bot": Mock()}
        await SessionMiddleware()(handler, event, data)
        session, handler_data = handler.await_args.args
        return session, handler_data

    @pytest.mark.asyncio
    async def test_message_session_has_no_popup(self):
        session, handler_data = await self.build(EventContextFactory())

        assert isinstance(session, Session)
        assert isinstance(session.context_service, AiogramContextService)
        assert isinstance(session.message_service, AiogramMessageService)
        assert session.popup_service is None
        assert handler_data == {}

    @pytest.mark.asyncio
    async def test_button_press_session_has_popup_for_that_query(self):
        session, _ = await self.build(
            EventContextFactory(event_type=EventTypes.BUTTON_PRESSED, event_id="cq-9")
        )

        assert isinstance(session.popup_service, AiogramPopupService)
        assert session.popup_service.ctx.callback_query_id == "cq-9"


class TestErrorHandlingMiddleware(BaseTestGroup):
    async def run(self, session, error=None):
        handler = AsyncMock(side_effect=error, return_value="ok")
        result = await ErrorHandlingMiddleware()(handler, session, {})
        return handler, result

    @pytest.mark.asyncio
    async def test_success_passes_result_through(self, session):
        handler, result = await self.run(session)

        assert result == "ok"
        session.message_service.send_error_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_business_error_is_shown_to_user_and_keeps_context(self, session):
        await self.add_messages(session, 2)

        await self.run(session, InsufficientFunds())

        _, error = session.message_service.send_error_message.await_args.args
        assert isinstance(error, InsufficientFunds)
        assert len((await session.context_service.get_unprocessed()).messages) == 2

    @pytest.mark.asyncio
    async def test_unexpected_error_hides_details_and_resets_session(self, session):
        await self.add_messages(session, 2)
        await session.context_service.set_processing_state()

        await self.run(session, RuntimeError("secret internals"))

        _, error = session.message_service.send_error_message.await_args.args
        assert "secret internals" not in str(error)
        assert str(error) == "Ошибка! Обратитесь в техподдержку"
        with pytest.raises(ContextEmpty):
            await session.context_service.get_unprocessed()
        assert session.context_service._current_state is None
