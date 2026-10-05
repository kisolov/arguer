"""Деньги в Decimal до сотых; цена /go учитывает всю историю, которую видит модель."""

from decimal import Decimal

import pytest

from config import CostConfig
from src.application import AddMessageToUnprocessed
from src.domain.exceptions import ContextLimitExceeded
from src.domain.models import (
    Argue,
    Dialogue,
    Reasoning,
    Speaker,
    UnprocessedMessage,
    money,
)
from src.domain.operations import CostCalculator
from tests.cases.base import BaseTestGroup
from tests.utils.factories import EventContextFactory


def history(symbols: int) -> Argue:
    return Argue([Reasoning("я" * symbols, Speaker("a"))], Speaker("a"))


def dialogue(text: str) -> Dialogue:
    return Dialogue([UnprocessedMessage(Speaker("a"), text=text)])


class TestMoney(BaseTestGroup):
    @pytest.mark.parametrize(
        "raw, expected",
        [(Decimal("974.835"), "974.84"), (Decimal("0.005"), "0.01"), (3, "3.00")],
    )
    def test_rounds_half_up_to_cents(self, raw, expected):
        assert money(raw) == Decimal(expected)

    def test_float_is_rejected(self):
        with pytest.raises(TypeError):
            money(0.1)

    def test_cost_is_exact_decimal(self):
        cost = CostCalculator(CostConfig()).calculate_cost(
            voice_seconds=7, text_symbols=333
        )

        # 25 + 7·25/60 + 333·25/5000 = 25 + 2.91666… + 1.665 = 29.58166…
        assert cost == Decimal("29.58")

    def test_repeated_small_charges_do_not_drift(self):
        total = sum((money(Decimal("0.1")) for _ in range(10)), Decimal(0))

        assert total == Decimal("1.00")


class TestHistoryIsCharged(BaseTestGroup):
    @pytest.fixture
    def billing(self):
        return self.container.core.billing_service()

    def test_history_symbols_add_to_price(self, billing):
        new = dialogue("x" * 100)

        alone = billing.calculate_dialogue_cost(new)
        with_history = billing.calculate_dialogue_cost(new, history(5000))

        assert with_history - alone == Decimal("25.00")

    @pytest.mark.asyncio
    async def test_second_round_of_dispute_costs_more(self, session, go_uc):
        await self.add_messages(session, 2)
        await session.context_service.set_defendant(Speaker("человек 0"))
        await go_uc.execute()
        first = session.message_service.notify_charge.await_args.args[1]

        await self.add_messages(session, 2)
        await go_uc.execute()
        second = session.message_service.notify_charge.await_args.args[1]

        assert second > first


class TestContextLimit(BaseTestGroup):
    async def forward(self, session, text):
        session.event = EventContextFactory(
            user=session.user, data=text, forward_from_name="a", media=None
        )
        await AddMessageToUnprocessed(
            session, self.container.config.app_config()
        ).execute()

    @pytest.mark.asyncio
    async def test_message_over_limit_with_history_is_rejected(self, session):
        limit = self.container.config.app_config().context_symbols_limit
        await session.context_service.set_processed(history(limit - 10))
        await self.forward(session, "x" * 10)

        with pytest.raises(ContextLimitExceeded):
            await self.forward(session, "y")

        assert len((await session.context_service.get_unprocessed()).messages) == 1

    @pytest.mark.asyncio
    async def test_message_within_limit_is_accepted(self, session):
        await session.context_service.set_processed(history(100))

        await self.forward(session, "x" * 10)

        assert len((await session.context_service.get_unprocessed()).messages) == 1
