from typing import Dict, TypeVar, Generic, List
from src.domain.exceptions import RecordNotFound
from src.domain.models import User, Transaction, TransactionStatus
from src.domain.ports.repositories import (
    DomainRepository,
    UserRepository,
    TransactionRepository,
)

DomainEntity = TypeVar("DomainEntity")


class InMemoryRepository(DomainRepository[DomainEntity], Generic[DomainEntity]):
    """Базовый in-memory репозиторий"""

    def __init__(self):
        self._storage: Dict[int, DomainEntity] = {}
        self._next_id = 1

    async def store(self, domain_entity: DomainEntity) -> DomainEntity:
        if domain_entity.id is None:
            domain_entity.id = self._next_id
            self._next_id += 1

        self._storage[domain_entity.id] = domain_entity
        return domain_entity

    async def get(self, domain_entity: DomainEntity) -> DomainEntity:
        if domain_entity.id is None or domain_entity.id not in self._storage:
            raise RecordNotFound(domain_entity)

        return self._storage[domain_entity.id]


class InMemoryUserRepository(InMemoryRepository[User], UserRepository):
    """In-memory репозиторий для User"""

    async def get(self, user: User) -> User:
        if user.id and user.id in self._storage:
            return self._storage[user.id]

        # Поиск по telegram_id
        for stored_user in self._storage.values():
            if stored_user.telegram_id == user.telegram_id:
                return stored_user

        raise RecordNotFound(user)


class InMemoryTransactionRepository(
    InMemoryRepository[Transaction], TransactionRepository
):
    """In-memory репозиторий для Transaction"""

    async def get_pending_transactions_for(self, user_id: int) -> List[Transaction]:
        return [
            t
            for t in self._storage.values()
            if t.user.id == user_id and t.status == TransactionStatus.PENDING
        ]
