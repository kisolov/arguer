from typing import List, Dict, Any

from src.domain.models import PopupContext
from src.domain.ports import PopupService


class MockPopupService(PopupService):
    """Mock PopupService that tracks all shown popups in memory"""

    def __init__(self, callback_query_id):
        super().__init__(PopupContext(callback_query_id))
        self._shown_popups: List[Dict[str, Any]] = []

    async def show_popup(self, text: str, show_alert: bool = False):
        popup_record = {
            "callback_query_id": self.ctx.callback_query_id,
            "text": text,
            "show_alert": show_alert,
            "context": self.ctx,
        }
        self._shown_popups.append(popup_record)
