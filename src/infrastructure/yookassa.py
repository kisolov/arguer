from decimal import Decimal
import uuid
import asyncio
from yookassa import Payment as YooClient, Configuration
from yookassa.domain.response import PaymentResponse

from config import YooKassaConfig
from src.domain.models import TransactionStatus
from src.domain.ports import PaymentGateway, PaymentInfo


class YooKassaGateway(PaymentGateway):
    STATUS_MAPPING = {
        "pending": TransactionStatus.PENDING,
        "waiting_for_capture": TransactionStatus.PENDING,
        "succeeded": TransactionStatus.COMPLETED,
        "canceled": TransactionStatus.CANCELED,
    }

    def __init__(self, config: YooKassaConfig):
        Configuration.account_id = config.shop_id.get_secret_value()
        Configuration.secret_key = config.secret_key.get_secret_value()
        self.return_url = config.return_url

    async def create_payment(self, amount: Decimal | int, description: str) -> PaymentInfo:
        # Простой способ - без явного получения loop
        payment: PaymentResponse = await asyncio.to_thread(
            YooClient.create,
            {
                "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
                "confirmation": {"type": "redirect", "return_url": self.return_url},
                "capture": True,
                "description": description,
            },
            str(uuid.uuid4()),
        )
        return PaymentInfo(payment.confirmation.confirmation_url, payment.id)

    async def get_payment_status(self, payment_uuid: str) -> TransactionStatus:
        payment = await asyncio.to_thread(YooClient.find_one, payment_uuid)
        return self.STATUS_MAPPING.get(payment.status, TransactionStatus.PENDING)
