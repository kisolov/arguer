from .base import SessionRelatedUseCase
from src.domain.models import Transaction
from src.domain.operations import BillingService
from ..session import Session


class ChargeForUsage(SessionRelatedUseCase):
    def __init__(self, session: Session, billing_service: BillingService):
        super().__init__(session)
        self.billing_service = billing_service

    async def execute(self, dialogue) -> Transaction:
        cost = self.billing_service.calculate_dialogue_cost(dialogue)
        charge = await self.billing_service.charge_for_dialogue(
            self.session.user, dialogue
        )
        await self.session.message_service.notify_charge(
            self.session.answer_message_context, cost
        )
        return charge
