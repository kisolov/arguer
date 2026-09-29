from types import SimpleNamespace

import pytest
from pony import orm

from src.domain.exceptions import RecordNotFound
from src.domain.models import (
    Transaction,
    TransactionCategory,
    TransactionStatus,
    User,
)
from src.infrastructure.pony import PonyTransactionRepository, PonyUserRepository
from src.infrastructure.pony.models import db
from src.infrastructure.pony.setup import setup_pony
from tests.cases.base import BaseTestGroup


@pytest.fixture(scope="module")
def pony_db():
    """Реальные репозитории поверх sqlite в памяти: без MySQL."""
    if db.provider is None:
        setup_pony(SimpleNamespace(provider="sqlite", filename=":memory:"))
    yield db


class PonyTestGroup(BaseTestGroup):
    @pytest.fixture(autouse=True)
    def clean_tables(self, pony_db):
        with orm.db_session:
            orm.delete(t for t in pony_db.Transaction)
            orm.delete(u for u in pony_db.User)


class TestPonyUserRepository(PonyTestGroup):
    @pytest.fixture
    def users(self):
        return PonyUserRepository()

    def test_store_creates_user_with_default_balance(self, users):
        stored = users.store(User(telegram_id=100))

        assert stored.id is not None
        assert (stored.telegram_id, stored.bal) == (100, 150)

    def test_store_updates_existing_user(self, users):
        stored = users.store(User(telegram_id=100))
        stored.bal = 42

        users.store(stored)

        assert users.get(User(telegram_id=100)).bal == 42

    def test_get_by_telegram_id(self, users):
        stored = users.store(User(telegram_id=101))

        assert users.get(User(telegram_id=101)).id == stored.id

    def test_get_by_internal_id(self, users):
        stored = users.store(User(telegram_id=102))

        assert users.get(User(telegram_id=0, id=stored.id)).telegram_id == 102

    def test_get_unknown_user_raises(self, users):
        with pytest.raises(RecordNotFound):
            users.get(User(telegram_id=404))

    def test_store_does_not_duplicate_by_telegram_id(self, users):
        first = users.store(User(telegram_id=103))
        second = users.store(User(telegram_id=103, bal=1))

        assert first.id == second.id


class TestPonyTransactionRepository(PonyTestGroup):
    @pytest.fixture
    def users(self):
        return PonyUserRepository()

    @pytest.fixture
    def transactions(self):
        return PonyTransactionRepository()

    @pytest.fixture
    def owner(self, users):
        return users.store(User(telegram_id=200))

    def test_store_persists_transaction_with_enums(self, transactions, owner):
        stored = transactions.store(
            Transaction(
                user=owner,
                category=TransactionCategory.TOP_UP,
                amount=500,
                uuid="pay-1",
            )
        )

        assert stored.id is not None
        assert stored.category is TransactionCategory.TOP_UP
        assert stored.status is TransactionStatus.PENDING
        assert (stored.uuid, stored.amount, stored.user.id) == ("pay-1", 500, owner.id)

    def test_pending_lists_only_pending_of_that_user(
        self, transactions, users, owner
    ):
        other = users.store(User(telegram_id=201))
        pending = transactions.store(
            Transaction(user=owner, category=TransactionCategory.TOP_UP, amount=1)
        )
        transactions.store(
            Transaction(
                user=owner,
                category=TransactionCategory.USAGE,
                amount=-1,
                status=TransactionStatus.COMPLETED,
            )
        )
        transactions.store(
            Transaction(user=other, category=TransactionCategory.TOP_UP, amount=1)
        )

        result = transactions.get_pending_transactions_for(owner.id)

        assert [t.id for t in result] == [pending.id]

    def test_status_change_is_persisted(self, transactions, owner):
        stored = transactions.store(
            Transaction(user=owner, category=TransactionCategory.TOP_UP, amount=1)
        )
        stored.status = TransactionStatus.COMPLETED

        transactions.store(stored)

        assert transactions.get_pending_transactions_for(owner.id) == []
        assert transactions.get(stored).status is TransactionStatus.COMPLETED

    def test_get_without_id_raises(self, transactions, owner):
        with pytest.raises(RecordNotFound):
            transactions.get(
                Transaction(user=owner, category=TransactionCategory.TOP_UP, amount=1)
            )
