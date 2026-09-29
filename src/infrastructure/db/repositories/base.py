from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import fields
from typing import Generic, Optional, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import RecordNotFound
from ..setup import Database

DomainEntity = TypeVar("DomainEntity")
DbEntity = TypeVar("DbEntity")


class SqlRepositoryAdapter(Generic[DomainEntity, DbEntity], ABC):
    """Без привязанной сессии: одна сессия на операцию, общего состояния между вызовами нет.

    С привязанной сессией (репозиторий внутри UnitOfWork) работает в её транзакции
    и сам ничего не коммитит: коммитом управляет UnitOfWork.
    """

    def __init__(self, database: Database, session: Optional[AsyncSession] = None):
        self._sessions = database.sessions
        self._bound_session = session

    @asynccontextmanager
    async def _read(self):
        if self._bound_session is not None:
            yield self._bound_session
            return
        async with self._sessions() as session:
            yield session

    @asynccontextmanager
    async def _write(self):
        if self._bound_session is not None:
            yield self._bound_session
            return
        async with self._sessions() as session, session.begin():
            yield session

    async def get(self, domain_entity: DomainEntity) -> DomainEntity:
        async with self._read() as session:
            return self._map(await self._get(session, domain_entity))

    async def store(self, domain_entity: DomainEntity) -> DomainEntity:
        async with self._write() as session:
            try:
                db_entity = await self._get(session, domain_entity)
                self._merge(domain_entity, db_entity)
            except RecordNotFound:
                db_entity = await self._create(session, domain_entity)
            await session.flush()
            return self._map(db_entity)

    def _merge(self, domain_entity: DomainEntity, db_entity: DbEntity) -> None:
        for field_ in fields(domain_entity):
            if not field_.metadata.get("ignore", False):
                setattr(db_entity, field_.name, getattr(domain_entity, field_.name))

    @abstractmethod
    async def _get(
        self, session: AsyncSession, domain_entity: DomainEntity
    ) -> DbEntity: ...

    @abstractmethod
    async def _create(
        self, session: AsyncSession, domain_entity: DomainEntity
    ) -> DbEntity: ...

    @abstractmethod
    def _map(self, db_entity: DbEntity) -> DomainEntity: ...
