
from .base import SessionRelatedUseCase
from ..session import Session
from src.domain.models import MessageContext
from src.domain.ports.repositories import BuyOptionsRepository


class SendPricesMenu(SessionRelatedUseCase):
    def __init__(self, session: Session, buy_options_repository: BuyOptionsRepository):
        super().__init__(session)
        self.buy_options_repository = buy_options_repository

    async def execute(self):
        await self.session.message_service.send_prices_menu(
            MessageContext(self.session.user, self.session.event.event_message_id),
            await self.buy_options_repository.get_all(),
        )
