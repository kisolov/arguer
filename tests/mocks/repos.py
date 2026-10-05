from decimal import Decimal
from copy import deepcopy
from typing import Dict, TypeVar, Generic, List
from src.domain.exceptions import InsufficientFunds, RecordNotFound
from src.domain.models import User, Transaction, TransactionStatus
from src.domain.ports.repositories import (
    DomainRepository,
    UserRepository,
    TransactionRepository,
)

DomainEntity = TypeVar("DomainEntity")


class InMemoryRepository(DomainRepository[DomainEntity], Generic[DomainEntity]):
    """Базовый in-memory репозиторий.

    Как и SQL-адаптер, принимает и отдаёт копии: изменение объекта вызывающим
    не попадает в хранилище, пока он не вызовет store.
    """

    def __init__(self):
        self._storage: Dict[int, DomainEntity] = {}
        self._next_id = 1

    async def store(self, domain_entity: DomainEntity) -> DomainEntity:
        stored = deepcopy(domain_entity)
        if stored.id is None:
            stored.id = self._next_id
        self._next_id = max(self._next_id, stored.id + 1)

        self._storage[stored.id] = stored
        return deepcopy(stored)

    async def get(self, domain_entity: DomainEntity) -> DomainEntity:
        if domain_entity.id is None or domain_entity.id not in self._storage:
            raise RecordNotFound(domain_entity)

        return deepcopy(self._storage[domain_entity.id])


class InMemoryUserRepository(InMemoryRepository[User], UserRepository):
    """In-memory репозиторий для User"""

    async def get(self, user: User) -> User:
        if user.id and user.id in self._storage:
            return deepcopy(self._storage[user.id])

        # Поиск по telegram_id
        for stored_user in self._storage.values():
            if stored_user.telegram_id == user.telegram_id:
                return deepcopy(stored_user)

        raise RecordNotFound(user)

    async def get_or_create(self, user: User) -> User:
        try:
            return await self.get(user)
        except RecordNotFound:
            return await self.store(user)

    async def change_balance(self, user_id: int, delta: Decimal) -> User:
        stored = self._storage.get(user_id)
        if stored is None:
            raise RecordNotFound(f"User[{user_id}]")
        if stored.bal + delta < 0:
            raise InsufficientFunds()
        stored.bal += delta
        return deepcopy(stored)


class InMemoryTransactionRepository(
    InMemoryRepository[Transaction], TransactionRepository
):
    """In-memory репозиторий для Transaction"""

    async def get_pending_transactions_for(self, user_id: int) -> List[Transaction]:
        return [
            deepcopy(t)
            for t in self._storage.values()
            if t.user.id == user_id and t.status == TransactionStatus.PENDING
        ]

    async def transition_pending(
        self, transaction_id: int, status: TransactionStatus
    ) -> bool:
        stored = self._storage.get(transaction_id)
        if stored is None or stored.status != TransactionStatus.PENDING:
            return False
        stored.status = status
        return True
