from src.domain.models import MessageContext
from src.domain.ports import MessageService
from .base import AutoMockMixin


class MockMessageService(AutoMockMixin, MessageService):
    def __init__(self):
        self._sent_messages = []
        self._deleted_messages = []
        self._message_counter = 0

        super().__init__()

    async def _send_message(
        self, ctx: MessageContext, text: str, *args, **kwargs
    ) -> MessageContext:
        self._message_counter += 1
        message_id = ctx.message_id or self._message_counter
        new_ctx = MessageContext(ctx.user, message_id)

        self._sent_messages.append(
            {
                "context": new_ctx,
                "text": text,
                "args": args,
                "kwargs": kwargs,
                "original_context": ctx,
            }
        )

        return new_ctx

    async def delete_message(self, ctx: MessageContext):
        self._deleted_messages.append(ctx)

    def get_sent_messages(self):
        return self._sent_messages.copy()

    def get_deleted_messages(self):
        return self._deleted_messages.copy()
