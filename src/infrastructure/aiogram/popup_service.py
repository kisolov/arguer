import aiogram

from src.domain.models import PopupContext
from src.domain.ports import PopupService


class AiogramPopupService(PopupService):
    def __init__(self, bot: aiogram.Bot, ctx: PopupContext):
        self.bot = bot
        super().__init__(ctx)

    async def _show_popup(self, text: str, show_alert: bool = False):
        await self.bot.answer_callback_query(
            self.ctx.callback_query_id, text, show_alert
        )
