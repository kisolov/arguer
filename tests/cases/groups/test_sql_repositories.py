import asyncio
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from src.application import EnsureUserExists
from src.domain.exceptions import RecordNotFound
from src.domain.models import (
    Transaction,
    TransactionCategory,
    TransactionStatus,
    User,
)
from src.infrastructure.db import Database, SqlTransactionRepository, SqlUserRepository
from src.infrastructure.db import models
from tests.cases.base import BaseTestGroup


@pytest_asyncio.fixture
async def database():
    """Реальные репозитории поверх sqlite в памяти: без MySQL."""
    db = Database.from_config(SimpleNamespace(provider="sqlite", filename=":memory:"))
    await db.create_schema()
    yield db
    await db.dispose()


class TestDatabaseConfig(BaseTestGroup):
    def test_mysql_url_is_built_from_config(self):
        config = SimpleNamespace(
            provider="mysql",
            host="db",
            port=3306,
            user="bot",
            password="p@ss/word",
            database="tg",
        )

        url = Database.from_config(config).engine.url

        assert url.drivername == "mysql+aiomysql"
        assert (url.host, url.port, url.username, url.database) == (
            "db",
            3306,
            "bot",
            "tg",
        )
        assert url.password == "p@ss/word"
        assert url.query["charset"] == "utf8mb4"


class TestSqlUserRepository(BaseTestGroup):
    @pytest.fixture
    def users(self, database):
        return SqlUserRepository(database)

    @pytest.mark.asyncio
    async def test_store_creates_user_with_default_balance(self, users):
        stored = await users.store(User(telegram_id=100))

        assert stored.id is not None
        assert (stored.telegram_id, stored.bal) == (100, 150)

    @pytest.mark.asyncio
    async def test_store_keeps_explicit_balance_on_create(self, users):
        stored = await users.store(User(telegram_id=100, bal=7))

        assert stored.bal == 7

    @pytest.mark.asyncio
    async def test_store_updates_existing_user(self, users):
        stored = await users.store(User(telegram_id=100))
        stored.bal = 42

        await users.store(stored)

        assert (await users.get(User(telegram_id=100))).bal == 42

    @pytest.mark.asyncio
    async def test_get_by_internal_id(self, users):
        stored = await users.store(User(telegram_id=102))

        assert (await users.get(User(telegram_id=0, id=stored.id))).telegram_id == 102

    @pytest.mark.asyncio
    async def test_get_unknown_user_raises(self, users):
        with pytest.raises(RecordNotFound):
            await users.get(User(telegram_id=404))

    @pytest.mark.asyncio
    async def test_store_does_not_duplicate_by_telegram_id(self, users):
        first = await users.store(User(telegram_id=103))
        second = await users.store(User(telegram_id=103, bal=1))

        assert first.id == second.id

    @pytest.mark.asyncio
    async def test_telegram_id_above_int32_survives_round_trip(self, users):
        big = 7_000_000_000

        await users.store(User(telegram_id=big))

        assert (await users.get(User(telegram_id=big))).telegram_id == big

    @pytest.mark.asyncio
    async def test_concurrent_stores_do_not_mix_sessions(self, tmp_path):
        # Файловая БД: у каждой сессии своё соединение, как в проде.
        # Общее in-memory соединение (StaticPool) параллельные транзакции не держит.
        db = Database.from_config(
            SimpleNamespace(provider="sqlite", filename=str(tmp_path / "concurrent.db"))
        )
        await db.create_schema()
        users = SqlUserRepository(db)

        stored = await asyncio.gather(
            *(users.store(User(telegram_id=1000 + i)) for i in range(5))
        )
        await db.dispose()

        assert sorted(u.telegram_id for u in stored) == list(range(1000, 1005))
        assert len({u.id for u in stored}) == 5


    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing_user(self, users):
        existing = await users.store(User(telegram_id=300, bal=5))

        got = await users.get_or_create(User(telegram_id=300))

        assert (got.id, got.bal) == (existing.id, 5)

    @pytest.mark.asyncio
    async def test_get_or_create_registers_unknown_user(self, users):
        got = await users.get_or_create(User(telegram_id=301))

        assert got.id is not None
        assert (await users.get(User(telegram_id=301))).id == got.id

    @pytest.mark.asyncio
    async def test_separate_processes_cannot_create_duplicates(self, tmp_path):
        # У каждого репозитория свой замок (как у отдельных процессов бота):
        # дубли отсекает уникальный индекс, проигравший перечитывает победителя.
        db = Database.from_config(
            SimpleNamespace(provider="sqlite", filename=str(tmp_path / "procs.db"))
        )
        await db.create_schema()
        repos = [SqlUserRepository(db) for _ in range(5)]

        got = await asyncio.gather(
            *(repo.get_or_create(User(telegram_id=666)) for repo in repos)
        )
        async with db.sessions() as session:
            rows = (await session.scalars(select(models.User))).all()
        await db.dispose()

        assert len({u.id for u in got}) == 1
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_legacy_duplicates_resolve_to_the_oldest_user(self, tmp_path):
        # В БД, созданной до уникального индекса, могли накопиться дубли
        db = Database.from_config(
            SimpleNamespace(provider="sqlite", filename=str(tmp_path / "legacy.db"))
        )
        await db.create_schema()
        async with db.engine.begin() as connection:
            await connection.execute(text("DROP INDEX ix_users_telegram_id"))
            for bal in (10, 20):
                await connection.execute(
                    text("INSERT INTO users (telegram_id, bal) VALUES (900, :bal)"),
                    {"bal": bal},
                )

        got = await SqlUserRepository(db).get(User(telegram_id=900))
        await db.dispose()

        assert (got.id, got.bal) == (1, 10)

    @pytest.mark.asyncio
    async def test_simultaneous_first_updates_register_one_user(self, tmp_path):
        # Пачка пересылок от нового пользователя обрабатывается параллельно.
        db = Database.from_config(
            SimpleNamespace(provider="sqlite", filename=str(tmp_path / "burst.db"))
        )
        await db.create_schema()
        users = SqlUserRepository(db)

        registered = await asyncio.gather(
            *(EnsureUserExists(users, telegram_id=555).execute() for _ in range(5))
        )
        async with db.sessions() as session:
            rows = (await session.scalars(select(models.User))).all()
        await db.dispose()

        assert len({u.id for u in registered}) == 1
        assert len(rows) == 1


class TestSqlTransactionRepository(BaseTestGroup):
    @pytest.fixture
    def users(self, database):
        return SqlUserRepository(database)

    @pytest.fixture
    def transactions(self, database):
        return SqlTransactionRepository(database)

    @pytest_asyncio.fixture
    async def owner(self, users):
        return await users.store(User(telegram_id=200))

    @pytest.mark.asyncio
    async def test_store_persists_transaction_with_enums(self, transactions, owner):
        stored = await transactions.store(
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

    @pytest.mark.asyncio
    async def test_created_at_round_trips(self, transactions, owner):
        original = Transaction(
            user=owner, category=TransactionCategory.TOP_UP, amount=1
        )

        stored = await transactions.store(original)

        assert stored.created_at == original.created_at

    @pytest.mark.asyncio
    async def test_pending_lists_only_pending_of_that_user(
        self, transactions, users, owner
    ):
        other = await users.store(User(telegram_id=201))
        pending = await transactions.store(
            Transaction(user=owner, category=TransactionCategory.TOP_UP, amount=1)
        )
        await transactions.store(
            Transaction(
                user=owner,
                category=TransactionCategory.USAGE,
                amount=-1,
                status=TransactionStatus.COMPLETED,
            )
        )
        await transactions.store(
            Transaction(user=other, category=TransactionCategory.TOP_UP, amount=1)
        )

        result = await transactions.get_pending_transactions_for(owner.id)

        assert [t.id for t in result] == [pending.id]
        assert result[0].user.telegram_id == 200

    @pytest.mark.asyncio
    async def test_status_change_is_persisted(self, transactions, owner):
        stored = await transactions.store(
            Transaction(user=owner, category=TransactionCategory.TOP_UP, amount=1)
        )
        stored.status = TransactionStatus.COMPLETED

        await transactions.store(stored)

        assert await transactions.get_pending_transactions_for(owner.id) == []
        assert (await transactions.get(stored)).status is TransactionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_get_without_id_raises(self, transactions, owner):
        with pytest.raises(RecordNotFound):
            await transactions.get(
                Transaction(user=owner, category=TransactionCategory.TOP_UP, amount=1)
            )

    @pytest.mark.asyncio
    async def test_get_unknown_id_raises_record_not_found(self, transactions, owner):
        with pytest.raises(RecordNotFound):
            await transactions.get(
                Transaction(
                    user=owner,
                    category=TransactionCategory.TOP_UP,
                    amount=1,
                    id=999,
                )
            )

    @pytest.mark.asyncio
    async def test_store_for_unknown_user_raises_record_not_found(self, transactions):
        ghost = User(telegram_id=1, id=999)

        with pytest.raises(RecordNotFound):
            await transactions.store(
                Transaction(user=ghost, category=TransactionCategory.TOP_UP, amount=1)
            )
