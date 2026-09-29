from .base import SessionRelatedUseCase
from ..session import Session
from src.domain.models import MessageContext


class SendBalanceMenu(SessionRelatedUseCase):
    def __init__(self, session: Session, formula: str):
        super().__init__(session)
        self.formula = formula

    async def execute(self, message_context: MessageContext = None):
        await self.session.message_service.send_balance_menu(
            message_context or self.session.answer_message_context, formula=self.formula
        )
