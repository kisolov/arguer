from src.domain.ports import UnitOfWork
from src.domain.ports.repositories import TransactionRepository, UserRepository


class InMemoryUnitOfWork(UnitOfWork):
    """Транзакционность не имитируется: in-memory хранилища пишут сразу."""

    def __init__(self, users: UserRepository, transactions: TransactionRepository):
        self.users = users
        self.transactions = transactions

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass
