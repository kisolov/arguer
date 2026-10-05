import asyncio
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import InsufficientFunds, RecordNotFound
from src.domain.models import User
from src.domain.ports.repositories import UserRepository
from .base import SqlRepositoryAdapter
from .mapper import SqlDomainMapper
from .. import models
from ..setup import Database


class SqlUserRepository(SqlRepositoryAdapter[User, models.User], UserRepository):
    def __init__(self, database: Database, session: Optional[AsyncSession] = None):
        super().__init__(database, session)
        # Пачка апдейтов от нового пользователя идёт параллельно. Замок сериализует
        # регистрацию внутри процесса (и в БД, созданной без уникального индекса),
        # уникальный индекс отсекает дубли между процессами.
        self._create_lock = asyncio.Lock()

    async def get_or_create(self, user: User) -> User:
        # Почти каждый апдейт — от уже зарегистрированного: читаем без замка,
        # иначе все апдейты всех пользователей шли бы через него по одному
        try:
            return await self.get(user)
        except RecordNotFound:
            pass
        async with self._create_lock:
            try:
                return await self.get(user)
            except RecordNotFound:
                pass
            try:
                return await self.store(user)
            except IntegrityError:
                # Параллельный вызов успел зарегистрировать этого пользователя
                return await self.get(user)

    def _map(self, db_user: models.User) -> User:
        return SqlDomainMapper().user_to_domain(db_user)

    async def _get(self, session: AsyncSession, domain_user: User) -> models.User:
        if domain_user.id:
            got = await session.get(models.User, domain_user.id)
        else:
            got = await session.scalar(
                select(models.User)
                .where(models.User.telegram_id == domain_user.telegram_id)
                .order_by(models.User.id)
                .limit(1)
            )
        if got is None:
            raise RecordNotFound(domain_user)
        return got

    async def _create(self, session: AsyncSession, domain_user: User) -> models.User:
        db_user = models.User(telegram_id=domain_user.telegram_id, bal=domain_user.bal)
        session.add(db_user)
        return db_user

    async def change_balance(self, user_id: int, delta: float) -> User:
        async with self._write() as session:
            # Условный UPDATE: проверка и изменение баланса атомарны, снимок не читается
            changed = await session.execute(
                update(models.User)
                .where(models.User.id == user_id, models.User.bal + delta >= 0)
                .values(bal=models.User.bal + delta)
                .execution_options(synchronize_session=False)
            )
            if changed.rowcount == 0:
                if await session.get(models.User, user_id) is None:
                    raise RecordNotFound(f"User[{user_id}]")
                raise InsufficientFunds()
            db_user = await session.get(models.User, user_id, populate_existing=True)
            return self._map(db_user)
