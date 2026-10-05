from .base import SessionRelatedUseCase
from ..session import Session

from src.domain.ports import PaymentGateway
from src.domain.ports.repositories import BuyOptionsRepository
from src.domain.models import MessageContext
from src.domain.operations import BillingService


class SendPaymentLink(SessionRelatedUseCase):
    def __init__(
        self,
        session: Session,
        payment_gateway: PaymentGateway,
        buy_options_repository: BuyOptionsRepository,
        billing_service: BillingService,
    ):
        super().__init__(session)
        self.payment_gateway = payment_gateway
        self.buy_options_repository = buy_options_repository
        self.billing_service = billing_service

    async def execute(self):
        """Ссылка уходит пользователю, только когда платёж записан и привязан к транзакции.

        Иначе можно было бы оплатить платёж, о котором не знает БД, и баланс бы
        не пополнился. Без ссылки неоплаченный платёж просто истекает в ЮKassa.
        """
        buy_option = await self.buy_options_repository.get(
            self.session.event.data.option_index
        )
        transaction = await self.billing_service.open_top_up(
            self.session.user, buy_option.tokens_amount
        )
        try:
            payment = await self.payment_gateway.create_payment(
                buy_option.price, buy_option.description
            )
        except Exception:
            await self.billing_service.cancel_transaction(transaction)
            raise
        await self.billing_service.attach_payment(transaction, payment.payment_uuid)

        await self.session.message_service.send_payment_link(
            MessageContext(self.session.user, self.session.event.event_message_id),
            payment.confirmation_url,
        )
