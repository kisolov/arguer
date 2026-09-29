from abc import ABC

from src.domain.models import User
from src.domain.ports.repositories import DomainRepository


class UserRepository(DomainRepository[User], ABC): ...
