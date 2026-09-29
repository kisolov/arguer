from dataclasses import replace
from typing import Callable

from src.domain.models import (
    TransactionCategory,
    TransactionStatus,
    Transaction,
    User,
    Dialogue,
)
from .cost_calculator import CostCalculator
from src.domain.ports import UnitOfWork
from src.domain.ports.repositories import TransactionRepository


class BillingService:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        unit_of_work: Callable[[], UnitOfWork],
        cost_calculator: CostCalculator,
    ):
        self.transaction_repository = transaction_repository
        self.unit_of_work = unit_of_work
        self.cost_calculator = cost_calculator

    def calculate_dialogue_cost(self, dialogue: Dialogue):
        voice_seconds = sum(
            msg.media.duration for msg in dialogue.messages if msg.media
        )
        text_symbols = sum(len(msg.text) for msg in dialogue.messages if msg.text)

        return self.cost_calculator.calculate_cost(voice_seconds, text_symbols)

    async def charge_for_dialogue(self, user: User, dialogue: Dialogue):
        cost = self.calculate_dialogue_cost(dialogue)

        transaction = self._create_transaction(
            user, -cost, TransactionCategory.USAGE, TransactionStatus.COMPLETED
        )
        await self.apply_transaction(transaction)

    async def record_top_up(self, user: User, amount: float, uuid: str):
        transaction = self._create_transaction(
            user, amount, category=TransactionCategory.TOP_UP, uuid=uuid
        )
        await self.transaction_repository.store(transaction)

    def _create_transaction(
        self,
        user: User,
        amount: float,
        category: TransactionCategory,
        status: TransactionStatus = TransactionStatus.PENDING,
        uuid: str = None,
    ):
        return Transaction(
            user=user, amount=amount, category=category, status=status, uuid=uuid
        )

    async def apply_transaction(self, transaction: Transaction):
        """Начисляет или списывает сумму транзакции атомарно.

        Баланс меняется приращением в БД, а не записью снимка из памяти, поэтому
        параллельные начисления не теряются. Переданные объекты обновляются
        только после успешного коммита.
        """
        if transaction.id is None:
            await self._apply_new(transaction)
        else:
            await self._apply_pending(transaction)

    async def _apply_new(self, transaction: Transaction):
        completed = replace(transaction, status=TransactionStatus.COMPLETED)
        async with self.unit_of_work() as uow:
            user = await uow.users.change_balance(
                transaction.user.id, transaction.amount
            )
            stored = await uow.transactions.store(completed)

        transaction.id = stored.id
        transaction.status = TransactionStatus.COMPLETED
        transaction.user.bal = user.bal

    async def _apply_pending(self, transaction: Transaction):
        async with self.unit_of_work() as uow:
            applied = await uow.transactions.transition_pending(
                transaction.id, TransactionStatus.COMPLETED
            )
            if applied:
                user = await uow.users.change_balance(
                    transaction.user.id, transaction.amount
                )
                status = TransactionStatus.COMPLETED
            else:
                # Уже обработана параллельным вызовом: баланс не трогаем
                user = await uow.users.get(transaction.user)
                status = (await uow.transactions.get(transaction)).status

        transaction.status = status
        transaction.user.bal = user.bal

    async def cancel_transaction(self, transaction: Transaction):
        cancelled = await self.transaction_repository.transition_pending(
            transaction.id, TransactionStatus.CANCELED
        )
        if cancelled:
            transaction.status = TransactionStatus.CANCELED
        else:
            transaction.status = (
                await self.transaction_repository.get(transaction)
            ).status
