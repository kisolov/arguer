import pytest
import pytest_asyncio

from src.domain.exceptions import InsufficientFunds
from src.domain.models import (
    Dialogue,
    Media,
    Speaker,
    Transaction,
    TransactionCategory,
    TransactionStatus,
    UnprocessedMessage,
    User,
)
from tests.cases.base import BaseTestGroup


class TestBillingService(BaseTestGroup):
    @pytest.fixture
    def billing(self):
        return self.container.core.billing_service()

    @pytest.fixture
    def transactions(self):
        return self.container.interfaces.transaction_repository()

    @pytest.fixture
    def users(self):
        return self.container.interfaces.user_repository()

    @pytest_asyncio.fixture
    async def stored_user(self, users):
        return await users.store(User(telegram_id=42, bal=100))

    @pytest.fixture
    def dialogue(self):
        return Dialogue(
            [
                UnprocessedMessage(Speaker("a"), text="a" * 100),
                UnprocessedMessage(Speaker("b"), media=Media("x.ogg", 12)),
            ]
        )

    def test_dialogue_cost_matches_calculator(self, billing, dialogue):
        expected = billing.cost_calculator.calculate_cost(12, 100)

        assert billing.calculate_dialogue_cost(dialogue) == pytest.approx(expected)

    @pytest.mark.asyncio
    async def test_charge_decreases_balance_and_records_usage(
        self, billing, stored_user, dialogue, transactions
    ):
        cost = billing.calculate_dialogue_cost(dialogue)

        await billing.charge_for_dialogue(stored_user, dialogue)

        assert stored_user.bal == pytest.approx(100 - cost)
        usage = [
            t
            for t in transactions._storage.values()
            if t.user.id == stored_user.id and t.category == TransactionCategory.USAGE
        ]
        assert len(usage) == 1
        assert usage[0].status == TransactionStatus.COMPLETED
        assert usage[0].amount == pytest.approx(-cost)

    @pytest.mark.asyncio
    async def test_charge_with_insufficient_funds_keeps_balance(
        self, billing, users, dialogue
    ):
        poor = await users.store(User(telegram_id=43, bal=1))

        with pytest.raises(InsufficientFunds):
            await billing.charge_for_dialogue(poor, dialogue)

        assert poor.bal == 1

    @pytest.mark.asyncio
    async def test_record_top_up_stores_pending_transaction(
        self, billing, stored_user, transactions
    ):
        await billing.record_top_up(stored_user, 500, "pay-1")

        pending = await transactions.get_pending_transactions_for(stored_user.id)
        assert [(t.uuid, t.amount) for t in pending] == [("pay-1", 500)]
        assert stored_user.bal == 100

    @pytest.mark.asyncio
    async def test_apply_transaction_credits_balance_and_completes(
        self, billing, stored_user, transactions
    ):
        await billing.record_top_up(stored_user, 500, "pay-2")
        pending = (await transactions.get_pending_transactions_for(stored_user.id))[0]

        await billing.apply_transaction(pending)

        assert stored_user.bal == 600
        assert pending.status == TransactionStatus.COMPLETED
        assert await transactions.get_pending_transactions_for(stored_user.id) == []

    @pytest.mark.asyncio
    async def test_cancel_transaction_marks_canceled_without_touching_balance(
        self, billing, stored_user, transactions
    ):
        await billing.record_top_up(stored_user, 500, "pay-3")
        pending = (await transactions.get_pending_transactions_for(stored_user.id))[0]

        await billing.cancel_transaction(pending)

        assert pending.status == TransactionStatus.CANCELED
        assert stored_user.bal == 100

    @pytest.mark.asyncio
    async def test_apply_transaction_exact_balance_is_allowed(
        self, billing, stored_user
    ):
        transaction = Transaction(
            user=stored_user, category=TransactionCategory.USAGE, amount=-100
        )

        await billing.apply_transaction(transaction)

        assert stored_user.bal == 0
