from abc import ABC, abstractmethod

from src.domain.models import User
from src.domain.ports.repositories import DomainRepository


class UserRepository(DomainRepository[User], ABC):
    @abstractmethod
    async def get_or_create(self, user: User) -> User:
        """Возвращает пользователя с этим telegram_id, регистрируя его при первом обращении.

        Параллельные вызовы для одного telegram_id возвращают одну и ту же запись.
        """

    @abstractmethod
    async def change_balance(self, user_id: int, delta: float) -> User:
        """Атомарно прибавляет delta к балансу и возвращает свежего пользователя.

        Баланс не может стать отрицательным: тогда бросает InsufficientFunds.
        Нет такого пользователя: RecordNotFound.
        """
