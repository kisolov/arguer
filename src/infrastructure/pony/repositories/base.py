from abc import ABC
from functools import wraps
from typing import TypeVar

from pony import orm

from src.domain.ports.repositories import DomainRepositoryAdapter


def wrap_with_session(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with orm.db_session:
            result = func(*args, **kwargs)
        return result

    return wrapper


DomainEntity = TypeVar("DomainEntity")
PonyEntity = TypeVar("PonyEntity")


class PonyRepositoryAdapter(DomainRepositoryAdapter[DomainEntity, PonyEntity], ABC):
    def __init__(self):
        self._commit = orm.commit

        self.get = wrap_with_session(self.get)
        self.store = wrap_with_session(self.store)
