import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import RecordNotFound
from src.domain.models import User
from src.domain.ports.repositories import UserRepository
from .base import SqlRepositoryAdapter
from .mapper import SqlDomainMapper
from .. import models
from ..setup import Database


class SqlUserRepository(SqlRepositoryAdapter[User, models.User], UserRepository):
    def __init__(self, database: Database):
        super().__init__(database)
        # Пачка апдейтов от нового пользователя идёт параллельно: без замка
        # get-or-create создаст нескольких пользователей с одним telegram_id.
        self._store_lock = asyncio.Lock()

    async def store(self, domain_user: User) -> User:
        async with self._store_lock:
            return await super().store(domain_user)

    def _map(self, db_user: models.User) -> User:
        return SqlDomainMapper().user_to_domain(db_user)

    async def _get(self, session: AsyncSession, domain_user: User) -> models.User:
        if domain_user.id:
            got = await session.get(models.User, domain_user.id)
        else:
            got = await session.scalar(
                select(models.User)
                .where(models.User.telegram_id == domain_user.telegram_id)
                .limit(1)
            )
        if got is None:
            raise RecordNotFound(domain_user)
        return got

    async def _create(self, session: AsyncSession, domain_user: User) -> models.User:
        db_user = models.User(telegram_id=domain_user.telegram_id, bal=domain_user.bal)
        session.add(db_user)
        return db_user
