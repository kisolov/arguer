from .base import SessionRelatedUseCase
from src.domain.exceptions import UnknownDefendant
from src.domain.models import MessageContext


class SelectDefendant(SessionRelatedUseCase):
    """Кнопка несёт номер варианта из меню, а не имя.

    Имя в callback_data не помещается в 64 байта и ломается на двоеточии,
    поэтому варианты сохраняются в контексте при показе меню.
    """

    async def execute(self):
        context = self.session.context_service
        options = await context.get_defendant_options()
        index = self.session.event.data.defendant_index
        if not 0 <= index < len(options):
            raise UnknownDefendant()

        chosen = options[index]
        if chosen not in (await context.get_unprocessed()).participants:
            raise UnknownDefendant()

        await self.session.message_service.delete_message(
            MessageContext(self.session.user, self.session.event.event_message_id)
        )
        await context.set_defendant(chosen)
        await context.clear_state()
