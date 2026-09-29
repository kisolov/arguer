from abc import ABC, abstractmethod
from typing import List

from src.domain.models import Transaction
from src.domain.ports.repositories import DomainRepository


class TransactionRepository(DomainRepository[Transaction], ABC):
    @abstractmethod
    async def get_pending_transactions_for(self, user_id: int) -> List[Transaction]: ...
