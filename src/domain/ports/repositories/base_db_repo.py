from abc import ABC, abstractmethod
from typing import Generic, TypeVar

DomainEntity = TypeVar("DomainEntity")


class DomainRepository(Generic[DomainEntity], ABC):
    @abstractmethod
    async def store(self, domain_entity: DomainEntity) -> DomainEntity: ...

    @abstractmethod
    async def get(self, domain_entity: DomainEntity) -> DomainEntity: ...
