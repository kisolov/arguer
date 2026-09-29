import pytest

from src.presentation.aiogram import routes
from tests.cases.base import BaseTestGroup
from tests.utils.factories import EventContextFactory


class TestCallbackRoutes(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_ctx_reports_collected_context(self, session):
        await self.add_messages(session, 2)

        await routes.show_ctx(session)

        session.message_service.send_context_info.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_top_up_opens_prices_menu_in_pressed_message(self, session):
        session.event = EventContextFactory(user=session.user, event_message_id=41)

        await routes.top_up(session)

        ctx, options = session.message_service.send_prices_menu.await_args.args
        assert ctx.message_id == 41
        assert len(options) == 4

    @pytest.mark.asyncio
    async def test_back_returns_to_balance_menu_in_same_message(self, session):
        session.event = EventContextFactory(user=session.user, event_message_id=41)

        await routes.buy_options_back(session)

        ctx = session.message_service.send_balance_menu.await_args.args[0]
        assert ctx.message_id == 41
