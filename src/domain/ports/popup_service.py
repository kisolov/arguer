from abc import ABC, abstractmethod

from src.domain.models import PopupContext


class Popups:
    UPDATED = "Обновлено"


class PopupService(ABC):
    def __init__(self, ctx: PopupContext):
        self.ctx = ctx

    @abstractmethod
    async def _show_popup(self, text: str, show_alert: bool = False): ...

    async def notify_updated(self):
        await self._show_popup(Popups.UPDATED)
