from src.domain.ports import UnitOfWork
from .repositories import SqlTransactionRepository, SqlUserRepository
from .setup import Database


class SqlUnitOfWork(UnitOfWork):
    """Новый экземпляр на сценарий: своя сессия, своя транзакция, репозитории на ней."""

    def __init__(self, database: Database):
        self._database = database

    async def __aenter__(self) -> "SqlUnitOfWork":
        self._session = self._database.sessions()
        await self._session.begin()
        self.users = SqlUserRepository(self._database, session=self._session)
        self.transactions = SqlTransactionRepository(
            self._database, session=self._session
        )
        return self

    async def commit(self) -> None:
        try:
            await self._session.commit()
        finally:
            await self._session.close()

    async def rollback(self) -> None:
        try:
            await self._session.rollback()
        finally:
            await self._session.close()
