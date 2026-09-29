from .base import SessionRelatedUseCase
from ..session import Session
from src.domain.ports import PaymentGateway
from src.domain.ports.repositories import TransactionRepository
from src.domain.models import TransactionStatus, MessageContext
from src.domain.operations import BillingService


class RefreshBalance(SessionRelatedUseCase):
    def __init__(
        self,
        session: Session,
        payment_gateway: PaymentGateway,
        transaction_repository: TransactionRepository,
        billing_service: BillingService,
        formula: str,
    ):
        super().__init__(session)
        self.payment_gateway = payment_gateway
        self.transaction_repo = transaction_repository
        self.billing_service = billing_service
        self.formula = formula

    async def execute(self):
        pending = self.transaction_repo.get_pending_transactions_for(
            self.session.user.id
        )
        if not pending:
            return await self._notify_updated()

        for transaction in pending:
            if not transaction.uuid:
                continue

            status = await self.payment_gateway.get_payment_status(transaction.uuid)
            await self._process_transaction(transaction, status)

        await self._notify_updated()

    async def _process_transaction(self, transaction, status: TransactionStatus):
        if status is TransactionStatus.COMPLETED:
            self.billing_service.apply_transaction(transaction)
            self.session.event.user = transaction.user
            await self._update_window()
        elif status is TransactionStatus.CANCELED:
            self.billing_service.cancel_transaction(transaction)

    async def _notify_updated(self):
        await self.session.popup_service.notify_updated()

    async def _update_window(self):
        await self.session.message_service.send_balance_menu(
            MessageContext(
                self.session.event.user, self.session.event.event_message_id
            ),
            self.formula,
        )
