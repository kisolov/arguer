from abc import ABC, abstractmethod

from src.domain.models import User
from src.domain.ports.repositories import DomainRepository


class UserRepository(DomainRepository[User], ABC):
    @abstractmethod
    async def change_balance(self, user_id: int, delta: float) -> User:
        """Атомарно прибавляет delta к балансу и возвращает свежего пользователя.

        Баланс не может стать отрицательным: тогда бросает InsufficientFunds.
        Нет такого пользователя: RecordNotFound.
        """
