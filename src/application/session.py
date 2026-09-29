from typing import Optional

from src.domain.models import EventContext, MessageContext
from src.domain.ports import ContextService, MessageService, PopupService


class Session:
    def __init__(
        self,
        event: EventContext,
        context_service: ContextService,
        message_service: MessageService,
        popup_service: Optional[PopupService] = None,
    ):
        self.event = event
        self.context_service = context_service
        self.message_service = message_service
        self.popup_service = popup_service

    @property
    def user(self):
        return self.event.user

    @property
    def answer_message_context(self):
        return MessageContext(user=self.user)

    @property
    def popup_allowed(self):
        return bool(self.popup_service)
