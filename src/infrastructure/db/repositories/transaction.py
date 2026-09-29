from typing import List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.exceptions import RecordNotFound
from src.domain.models import Transaction, TransactionStatus
from src.domain.ports.repositories import TransactionRepository
from .base import SqlRepositoryAdapter
from .mapper import SqlDomainMapper
from .. import models

_WITH_USER = selectinload(models.Transaction.user)


class SqlTransactionRepository(
    SqlRepositoryAdapter[Transaction, models.Transaction], TransactionRepository
):
    def _map(self, db_transaction: models.Transaction) -> Transaction:
        return SqlDomainMapper().transaction_to_domain(db_transaction)

    async def _get(
        self, session: AsyncSession, domain_transaction: Transaction
    ) -> models.Transaction:
        if not domain_transaction.id:
            raise RecordNotFound(domain_transaction)
        got = await session.get(
            models.Transaction, domain_transaction.id, options=[_WITH_USER]
        )
        if got is None:
            raise RecordNotFound(domain_transaction)
        return got

    async def _create(
        self, session: AsyncSession, transaction: Transaction
    ) -> models.Transaction:
        db_user = await session.get(models.User, transaction.user.id)
        if db_user is None:
            raise RecordNotFound(transaction.user)
        db_transaction = models.Transaction(
            user=db_user,
            status=transaction.status,
            category=transaction.category,
            amount=transaction.amount,
            created_at=transaction.created_at,
            uuid=transaction.uuid,
        )
        session.add(db_transaction)
        return db_transaction

    async def get_pending_transactions_for(self, user_id: int) -> List[Transaction]:
        async with self._read() as session:
            rows = await session.scalars(
                select(models.Transaction)
                .where(
                    models.Transaction.user_id == user_id,
                    models.Transaction.status == TransactionStatus.PENDING,
                )
                .options(_WITH_USER)
            )
            return [self._map(t) for t in rows]

    async def transition_pending(
        self, transaction_id: int, status: TransactionStatus
    ) -> bool:
        async with self._write() as session:
            # Compare-and-set: переход выигрывает ровно один из параллельных вызовов
            changed = await session.execute(
                update(models.Transaction)
                .where(
                    models.Transaction.id == transaction_id,
                    models.Transaction.status == TransactionStatus.PENDING,
                )
                .values(status=status)
                .execution_options(synchronize_session=False)
            )
            return changed.rowcount == 1
