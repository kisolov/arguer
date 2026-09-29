from abc import abstractmethod, ABC

from src.domain.exceptions import ContextEmpty, UndefinedDefendant
from src.domain.models import Dialogue, Speaker, Argue


class ContextService(ABC):
    @abstractmethod
    async def get(self, key: str): ...
    @abstractmethod
    async def update(self, values: dict): ...
    @abstractmethod
    async def set(self, values: dict): ...
    @abstractmethod
    async def clear_data(self): ...
    @abstractmethod
    async def clear_state(self) -> None: ...

    async def get_unprocessed(self) -> Dialogue:
        try:
            return await self.get("unprocessed")
        except KeyError:
            raise ContextEmpty()

    async def get_defendant(self) -> Speaker:
        try:
            return await self.get("defendant")
        except KeyError:
            raise UndefinedDefendant()

    async def set_unprocessed(self, dialogue: Dialogue):
        await self.update(dict(unprocessed=dialogue))

    async def set_defendant(self, defendant: Speaker):
        await self.update(dict(defendant=defendant))

    async def set_processed(self, argue: Argue):
        await self.update(dict(processed=argue))

    async def get_processed(self) -> Argue | None:
        try:
            return await self.get("processed")
        except KeyError:
            return None

    @abstractmethod
    async def set_processing_state(self) -> None: ...

    @abstractmethod
    async def set_defendant_selection_state(self) -> None: ...
