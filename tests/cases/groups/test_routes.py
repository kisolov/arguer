from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from di import container as app_container
from src.domain.exceptions import UndefinedDefendant
from src.presentation.aiogram import routes
from tests.cases.base import BaseTestGroup


class TestWithDeps(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_explicit_kwarg_wins_over_container(self):
        seen = {}

        @routes.with_deps("core.cost_calculator")
        async def handler(event, **kwargs):
            seen.update(kwargs)

        await handler("event", cost_calculator="explicit")

        assert seen["cost_calculator"] == "explicit"

    @pytest.mark.asyncio
    async def test_dependency_is_injected_when_not_given(self):
        seen = {}

        @routes.with_deps("core.cost_calculator")
        async def handler(event, **kwargs):
            seen.update(kwargs)

        await handler("event")

        assert seen["cost_calculator"] is app_container.core.cost_calculator()


class TestGoRoute(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_missing_defendant_offers_selection_instead_of_failing(
        self, session
    ):
        await self.add_messages(session, 4)

        with patch.object(routes, "Go") as go:
            go.return_value.execute = AsyncMock(side_effect=UndefinedDefendant())
            await routes.go(session)

        assert session.context_service._current_state == "defendant_selection"
        session.message_service.send_defendant_selection.assert_awaited_once()


class TestCommandRoutes(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_start_sends_instructions(self, session):
        await routes.start(session)

        session.message_service.send_instructions.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_bal_sends_menu_with_cost_formula(self, session):
        await routes.bal(session)

        formula = session.message_service.send_balance_menu.await_args.kwargs["formula"]
        assert "✨" in formula

    @pytest.mark.asyncio
    async def test_clear_resets_context(self, session):
        await self.add_messages(session, 2)

        await routes.clear(session)

        session.message_service.notify_context_clean.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_forwarded_message_is_collected(self, session):
        from tests.utils.factories import EventContextFactory

        session.event = EventContextFactory(
            user=session.user, data="привет", forward_from_name="Аня"
        )

        await routes.handle_forwarded_message(session)

        assert len((await session.context_service.get_unprocessed()).messages) == 1

    @pytest.mark.asyncio
    async def test_input_is_swallowed_while_processing(self, session):
        assert await routes.processing_input_protection(session) is None


class TestTestMessageRoute(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_text_with_id_becomes_message_from_that_sender(self, session):
        from tests.utils.factories import EventContextFactory

        session.event = EventContextFactory(user=session.user, data="Земля плоская (7)")

        await routes.handle_test_message(session)

        message = (await session.context_service.get_unprocessed()).messages[0]
        assert (message.speaker.name, message.text) == ("User 7", "Земля плоская")


class TestSetupRoutes(BaseTestGroup):
    @pytest.mark.parametrize("enabled, expected", [(False, 1), (True, 2)])
    def test_test_router_is_attached_only_when_enabled(self, enabled, expected):
        dp = Mock()

        with app_container.config.app_config.override(
            SimpleNamespace(enable_test_messages=enabled)
        ):
            routes.setup_routes(dp)

        assert dp.include_router.call_count == expected
        included = [c.args[0] for c in dp.include_router.call_args_list]
        assert (routes.test_router in included) is enabled
