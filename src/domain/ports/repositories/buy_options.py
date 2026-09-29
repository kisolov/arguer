from abc import ABC, abstractmethod
from typing import List

from src.domain.models import BuyOption


class BuyOptionsRepository(ABC):
    @abstractmethod
    async def get(self, option_id) -> BuyOption: ...

    @abstractmethod
    async def get_all(self) -> List[BuyOption]: ...
