"""Биллинг поверх реальных SQL-репозиториев: атомарность и идемпотентность начислений."""

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import pytest_asyncio

from config import CostConfig
from src.domain.exceptions import InsufficientFunds
from src.domain.models import (
    Transaction,
    TransactionCategory,
    TransactionStatus,
    User,
)
from src.domain.operations import BillingService, CostCalculator
from src.infrastructure.db import (
    Database,
    SqlTransactionRepository,
    SqlUnitOfWork,
    SqlUserRepository,
)
from tests.cases.base import BaseTestGroup


@pytest_asyncio.fixture
async def database(tmp_path):
    # Файловая БД: у каждой сессии своё соединение, как в проде
    db = Database.from_config(
        SimpleNamespace(provider="sqlite", filename=str(tmp_path / "billing.db"))
    )
    await db.create_schema()
    try:
        yield db
    finally:
        await db.dispose()


class TestBillingOverSql(BaseTestGroup):
    @pytest.fixture
    def users(self, database):
        return SqlUserRepository(database)

    @pytest.fixture
    def transactions(self, database):
        return SqlTransactionRepository(database)

    @pytest.fixture
    def billing(self, database, transactions):
        return BillingService(
            transaction_repository=transactions,
            unit_of_work=lambda: SqlUnitOfWork(database),
            cost_calculator=CostCalculator(CostConfig()),
        )

    @pytest_asyncio.fixture
    async def user(self, users):
        return await users.store(User(telegram_id=77, bal=150))

    @pytest.mark.asyncio
    async def test_two_pending_payments_are_both_credited(
        self, billing, users, transactions, user
    ):
        await billing.record_top_up(user, 100, "pay-a")
        await billing.record_top_up(user, 200, "pay-b")

        for pending in await transactions.get_pending_transactions_for(user.id):
            await billing.apply_transaction(pending)

        assert (await users.get(user)).bal == 450

    @pytest.mark.asyncio
    async def test_same_payment_processed_twice_credits_once(
        self, billing, users, transactions, user
    ):
        await billing.record_top_up(user, 100, "pay-a")
        first = (await transactions.get_pending_transactions_for(user.id))[0]
        second = (await transactions.get_pending_transactions_for(user.id))[0]

        await asyncio.gather(
            billing.apply_transaction(first), billing.apply_transaction(second)
        )

        assert (await users.get(user)).bal == 250
        assert await transactions.get_pending_transactions_for(user.id) == []

    @pytest.mark.asyncio
    async def test_stale_caller_object_is_refreshed_after_duplicate(
        self, billing, transactions, user
    ):
        await billing.record_top_up(user, 100, "pay-a")
        first = (await transactions.get_pending_transactions_for(user.id))[0]
        second = (await transactions.get_pending_transactions_for(user.id))[0]

        await billing.apply_transaction(first)
        await billing.apply_transaction(second)

        assert second.user.bal == 250

    @pytest.mark.asyncio
    async def test_usage_over_balance_leaves_no_record(
        self, billing, users, database, user
    ):
        usage = Transaction(
            user=user, category=TransactionCategory.USAGE, amount=-1000
        )

        with pytest.raises(InsufficientFunds):
            await billing.apply_transaction(usage)

        assert (await users.get(user)).bal == 150
        async with SqlUnitOfWork(database) as uow:
            assert usage.id is None
            assert await uow.transactions.get_pending_transactions_for(user.id) == []

    @pytest.mark.asyncio
    async def test_failed_transaction_write_rolls_balance_back(
        self, billing, users, user
    ):
        usage = Transaction(user=user, category=TransactionCategory.USAGE, amount=-50)

        with patch.object(
            SqlTransactionRepository, "store", side_effect=RuntimeError("db down")
        ):
            with pytest.raises(RuntimeError, match="db down"):
                await billing.apply_transaction(usage)

        assert (await users.get(user)).bal == 150

    @pytest.mark.asyncio
    async def test_usage_is_recorded_and_debited_together(
        self, billing, users, transactions, user
    ):
        usage = Transaction(user=user, category=TransactionCategory.USAGE, amount=-50)

        await billing.apply_transaction(usage)

        assert (await users.get(user)).bal == 100
        assert usage.id is not None
        assert usage.status is TransactionStatus.COMPLETED
        assert user.bal == 100

    @pytest.mark.asyncio
    async def test_cancel_after_apply_does_not_reopen_completed(
        self, billing, users, transactions, user
    ):
        await billing.record_top_up(user, 100, "pay-a")
        pending = (await transactions.get_pending_transactions_for(user.id))[0]
        await billing.apply_transaction(pending)

        await billing.cancel_transaction(pending)

        stored = await transactions.get(pending)
        assert stored.status is TransactionStatus.COMPLETED
        assert (await users.get(user)).bal == 250

    @pytest.mark.asyncio
    async def test_refund_returns_charge_as_separate_record(
        self, billing, users, database, user
    ):
        charge = Transaction(user=user, category=TransactionCategory.USAGE, amount=-50)
        await billing.apply_transaction(charge)

        refund = await billing.refund(charge)

        assert (await users.get(user)).bal == 150
        async with SqlUnitOfWork(database) as uow:
            stored = await uow.transactions.get(refund)
        assert (stored.category, stored.amount, stored.status) == (
            TransactionCategory.REFUND,
            50,
            TransactionStatus.COMPLETED,
        )

    @pytest.mark.asyncio
    async def test_unattached_top_up_is_not_checked_until_payment_attached(
        self, billing, transactions, user
    ):
        opened = await billing.open_top_up(user, 100)
        [pending] = await transactions.get_pending_transactions_for(user.id)
        assert pending.uuid is None

        await billing.attach_payment(opened, "pay-a")

        [pending] = await transactions.get_pending_transactions_for(user.id)
        assert (pending.id, pending.uuid, pending.amount) == (opened.id, "pay-a", 100)
