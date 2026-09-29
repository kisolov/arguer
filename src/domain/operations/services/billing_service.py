from src.domain.exceptions import InsufficientFunds
from src.domain.models import (
    TransactionCategory,
    TransactionStatus,
    Transaction,
    User,
    Dialogue,
)
from .cost_calculator import CostCalculator
from src.domain.ports.repositories import TransactionRepository, UserRepository


class BillingService:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        user_repository: UserRepository,
        cost_calculator: CostCalculator,
    ):
        self.transaction_repository = transaction_repository
        self.user_repository = user_repository
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
        if transaction.user.bal + transaction.amount < 0:
            raise InsufficientFunds()
        transaction.status = TransactionStatus.COMPLETED
        transaction.user.bal += transaction.amount

        await self.transaction_repository.store(transaction)
        await self.user_repository.store(transaction.user)

    async def cancel_transaction(self, transaction: Transaction):
        transaction.status = TransactionStatus.CANCELED
        await self.transaction_repository.store(transaction)
