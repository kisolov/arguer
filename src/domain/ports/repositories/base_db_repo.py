from abc import ABC, abstractmethod
from dataclasses import fields
from typing import Generic, TypeVar

from src.domain.exceptions import RecordNotFound

DomainEntity = TypeVar("DomainEntity")
DatabaseEntity = TypeVar("DatabaseEntity")


class DomainRepository(Generic[DomainEntity], ABC):
    @abstractmethod
    def store(self, domain_entity: DomainEntity) -> DomainEntity: ...

    @abstractmethod
    def get(self, domain_entity: DomainEntity) -> DomainEntity: ...


class DomainRepositoryAdapter(
    Generic[DomainEntity, DatabaseEntity], DomainRepository[DomainEntity], ABC
):
    def store(self, domain_entity: DomainEntity) -> DomainEntity:
        try:
            db_entity = self._get(domain_entity)
            self._merge(domain_entity, db_entity)
        except RecordNotFound:
            db_entity = self._create(domain_entity)

        self._commit()
        return self._map(db_entity)

    @abstractmethod
    def _get(self, domain_entity: DomainEntity) -> DatabaseEntity: ...

    def _merge(self, domain_entity: DomainEntity, db_entity: DatabaseEntity):
        for field_ in fields(domain_entity):
            if not field_.metadata.get("ignore", False):
                setattr(db_entity, field_.name, getattr(domain_entity, field_.name))

    @abstractmethod
    def _create(self, domain_entity: DomainEntity) -> DatabaseEntity: ...

    def _commit(self): ...

    def _map(self, db_entity: DatabaseEntity) -> DomainEntity: ...

    def get(self, domain_entity: DomainEntity) -> DomainEntity:
        return self._map(self._get(domain_entity))
