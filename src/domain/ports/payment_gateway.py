from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.domain.models import TransactionStatus


@dataclass
class PaymentInfo:
    confirmation_url: str
    payment_uuid: str


class PaymentGateway(ABC):
    @abstractmethod
    async def create_payment(self, amount: float, description: str) -> PaymentInfo:
        pass

    @abstractmethod
    async def get_payment_status(self, payment_id: str) -> TransactionStatus:
        pass
