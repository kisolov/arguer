from src.domain.ports.repositories import UserRepository
from .base import AsyncUseCase
from src.domain.models import User


class EnsureUserExists(AsyncUseCase):
    def __init__(self, user_repo: UserRepository, telegram_id: int):
        self.telegram_id = telegram_id
        self.user_repo = user_repo

    async def execute(self):
        return await self.user_repo.get_or_create(User(telegram_id=self.telegram_id))
