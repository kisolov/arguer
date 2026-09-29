from abc import ABC, abstractmethod
from typing import List

from src.domain.models import Transaction, TransactionStatus
from src.domain.ports.repositories import DomainRepository


class TransactionRepository(DomainRepository[Transaction], ABC):
    @abstractmethod
    async def get_pending_transactions_for(self, user_id: int) -> List[Transaction]: ...

    @abstractmethod
    async def transition_pending(
        self, transaction_id: int, status: TransactionStatus
    ) -> bool:
        """Переводит транзакцию из PENDING в status, только если она ещё PENDING.

        True — переход выполнен этим вызовом, False — транзакцию уже обработали.
        """
