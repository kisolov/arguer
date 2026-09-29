from abc import ABC, abstractmethod
from typing import List

from src.domain.models import MessageContext, Speaker, BuyOption


class Texts:
    INSTRUCTIONS = (
        "Привет! Этот бот поможет тебе победить в любом споре."
        " Для этого просто перешли сюда переписку с человеком, которого хочешь переубедить,"
        " и затем напиши /go\n\nПополнить баланс - /bal\nОчистить контекст - /clear"
        "\n\n<b>У тебя {amount:.2f}✨</b>"
    )
    BALANCE_INFO = "На балансе <b>{balance:.2f}✨</b>\n\nЦена запроса рассчитывается по формуле <b>{formula}</b>"
    CHARGE_NOTIFICATION = "<b>{amount:.2f}✨</b>"
    CONTEXT_INFO = (
        "Контекст <b>{context_symbols} символов, {media_duration} секунд медиа.</b>\n\n"
        "Можно продолжить пересылать сообщения в этот контекст или написать /clear и начать сначала"
    )
    CONTEXT_CLEAN = "Контекст очищен. Можно начать сначала"
    PROGRESS_MESSAGE = "Идёт обработка..."
    DEFENDANT_SELECTION = "<b>Кого защищать?</b>"
    PRICES_MENU_TITLE = "<b>Варианты пополнения</b>"
    PAYMENT_LINK = "<b>Ссылка для оплаты - {link}</b>\n\nПосле завершения необходимо обновить баланс в меню /bal"


class MessageService(ABC):
    @abstractmethod
    async def delete_message(self, ctx: MessageContext): ...

    @abstractmethod
    async def _send_message(
        self, ctx: MessageContext, text: str, *args, **kwargs
    ) -> MessageContext: ...

    async def send_instructions(self, ctx: MessageContext):
        text = Texts.INSTRUCTIONS.format(amount=ctx.user.bal)
        return await self._send_message(ctx, text)

    async def send_error_message(
        self, ctx: MessageContext, exception: Exception | None = None
    ):
        return await self._send_message(ctx, str(exception or "Ошибка!"))

    async def send_balance_menu(self, ctx: MessageContext, formula: str):
        text = Texts.BALANCE_INFO.format(balance=ctx.user.bal, formula=formula)
        return await self._send_message(ctx, text)

    async def notify_charge(self, ctx: MessageContext, amount: float):
        return await self._send_message(
            ctx, Texts.CHARGE_NOTIFICATION.format(amount=amount)
        )

    async def send_resolution(self, ctx: MessageContext, resolution: str):
        return await self._send_message(ctx, resolution)

    async def send_context_info(
        self, ctx: MessageContext, context_symbols: int, context_media_duration: int
    ):
        return await self._send_message(
            ctx,
            Texts.CONTEXT_INFO.format(
                context_symbols=context_symbols, media_duration=context_media_duration
            ),
        )

    async def notify_context_clean(self, ctx: MessageContext):
        return await self._send_message(ctx, Texts.CONTEXT_CLEAN)

    async def send_progress_message(self, ctx: MessageContext):
        return await self._send_message(ctx, Texts.PROGRESS_MESSAGE)

    async def send_defendant_selection(
        self, ctx: MessageContext, variants: List[Speaker]
    ):
        await self._send_message(ctx, Texts.DEFENDANT_SELECTION)

    async def send_prices_menu(self, ctx: MessageContext, options: List[BuyOption]):
        await self._send_message(ctx, Texts.PRICES_MENU_TITLE)

    async def send_payment_link(self, ctx: MessageContext, link: str):
        await self._send_message(ctx, Texts.PAYMENT_LINK.format(link=link))
