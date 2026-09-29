from functools import wraps

from pony import orm

from src.domain.exceptions import RecordNotFound
from .base import PonyRepositoryAdapter
from .mapper import PonyDomainMapper
from .. import models
from src.domain.ports.repositories import UserRepository
from src.domain.models import User


class PonyUserRepository(PonyRepositoryAdapter[User, models.User], UserRepository):
    def __init__(self):
        super().__init__()
        self._map = PonyDomainMapper().user_to_domain

    @orm.db_session
    def _get(self, domain_user: User) -> User:
        if domain_user.id:
            got = self._get_by_internal_id(domain_user.id)
        else:
            got = self._get_by_telegram_id(domain_user.telegram_id)
        if not got:
            raise RecordNotFound(domain_user)
        return got

    @orm.db_session
    def _get_by_telegram_id(self, telegram_id: int) -> models.User:
        return orm.select(
            u for u in models.User if u.telegram_id == telegram_id
        ).first()

    @orm.db_session
    def _get_by_internal_id(self, internal_id: int) -> models.User:
        return models.User.get(id=internal_id)

    @orm.db_session
    def _create(self, domain_user: User) -> models.User:
        return models.User(telegram_id=domain_user.telegram_id)
