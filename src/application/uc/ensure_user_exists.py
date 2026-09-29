from src.domain.ports.repositories import UserRepository
from .base import AsyncUseCase
from src.domain.exceptions import RecordNotFound
from src.domain.models import User


class EnsureUserExists(AsyncUseCase):
    def __init__(self, user_repo: UserRepository, telegram_id: int):
        self.telegram_id = telegram_id
        self.user_repo = user_repo

    async def execute(self):
        desired_user = User(telegram_id=self.telegram_id)
        try:
            return await self.user_repo.get(desired_user)
        except RecordNotFound:
            return await self.user_repo.store(desired_user)
