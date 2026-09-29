from abc import ABC, abstractmethod

from ..session import Session


class UseCase(ABC):
    @abstractmethod
    def execute(self, *args, **kwargs): ...


class AsyncUseCase(ABC):
    @abstractmethod
    async def execute(self, *args, **kwargs): ...


class SessionRelatedUseCase(ABC):
    def __init__(self, session: Session):
        self.session = session
