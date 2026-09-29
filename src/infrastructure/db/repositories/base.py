from abc import ABC, abstractmethod
from dataclasses import fields
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import RecordNotFound
from ..setup import Database

DomainEntity = TypeVar("DomainEntity")
DbEntity = TypeVar("DbEntity")


class SqlRepositoryAdapter(Generic[DomainEntity, DbEntity], ABC):
    """Одна сессия на операцию: общего состояния между вызовами нет."""

    def __init__(self, database: Database):
        self._sessions = database.sessions

    async def get(self, domain_entity: DomainEntity) -> DomainEntity:
        async with self._sessions() as session:
            return self._map(await self._get(session, domain_entity))

    async def store(self, domain_entity: DomainEntity) -> DomainEntity:
        async with self._sessions() as session, session.begin():
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
