from typing import List

from pony import orm

from src.domain.exceptions import RecordNotFound
from src.domain.models import Transaction, TransactionStatus
from src.domain.ports.repositories import TransactionRepository
from .base import PonyRepositoryAdapter
from .mapper import PonyDomainMapper
from .. import models


class PonyTransactionRepository(
    PonyRepositoryAdapter[Transaction, models.Transaction], TransactionRepository
):
    def __init__(self):
        super().__init__()
        self._map = PonyDomainMapper().transaction_to_domain

    @orm.db_session
    def _get(self, domain_transaction: Transaction) -> models.Transaction:
        if domain_transaction.id:
            return models.Transaction[domain_transaction.id]
        else:
            raise RecordNotFound(domain_transaction)

    @orm.db_session
    def _create(self, transaction: Transaction):
        return models.Transaction(
            user=models.User[transaction.user.id],
            status=transaction.status,
            category=transaction.category,
            amount=transaction.amount,
            created_at=transaction.created_at,
            uuid=transaction.uuid,
        )

    @orm.db_session
    def get_pending_transactions_for(self, user_id: int) -> List[Transaction]:
        transactions = models.Transaction.select(lambda t: t.user.id == user_id)
        return [
            self._map(t) for t in transactions if t.status == TransactionStatus.PENDING
        ]
