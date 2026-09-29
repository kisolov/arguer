from src.domain.exceptions import RecordNotFound
from src.domain.models import BuyOption
from src.domain.ports.repositories import BuyOptionsRepository


class InMemoryBuyOptionsRepository(BuyOptionsRepository):
    def __init__(self):
        self._options = [
            BuyOption(100, 20, "100✨"),
            BuyOption(500, 80, "500✨"),
            BuyOption(1000, 150, "1000✨"),
            BuyOption(5000, 650, "5000✨"),
        ]

    async def get(self, option_id: int):
        try:
            return self._options[option_id]
        except IndexError:
            raise RecordNotFound(f"BuyOption[{option_id}]")

    async def get_all(self):
        return self._options
