from abc import ABC, abstractmethod

from src.domain.ports.repositories import TransactionRepository, UserRepository


class UnitOfWork(ABC):
    """Одна транзакция БД на сценарий: выход без исключения коммитит, с исключением откатывает."""

    users: UserRepository
    transactions: TransactionRepository

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
