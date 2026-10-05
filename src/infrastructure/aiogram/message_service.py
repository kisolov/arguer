from typing import List
from aiogram import Bot, types
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.domain.models import MessageContext, Speaker, BuyOption
from src.domain.ports import MessageService, Texts
from .telegram_html import split_message, to_telegram_html


class Callbacks:
    class DefendantSelectionCallback(CallbackData, prefix="def_sel"):
        # Номер в меню: имя не влезает в 64 байта callback_data и может содержать ':'
        defendant_index: int

    class BuyOptionSelectionCallback(CallbackData, prefix="buy_options"):
        option_index: int


class Keyboards:
    @staticmethod
    def balance_menu() -> InlineKeyboardMarkup:
        return types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="🔄", callback_data="update"),
                    types.InlineKeyboardButton(
                        text="Пополнить", callback_data="top_up"
                    ),
                ]
            ]
        )

    @staticmethod
    def defendant_selection(variants: List[Speaker]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for index, variant in enumerate(variants):
            callback = Callbacks.DefendantSelectionCallback(defendant_index=index)
            builder.button(text=variant.name, callback_data=callback)
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def buy_options(options: List[BuyOption]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for indx, option in enumerate(options):
            builder.button(
                text=f"{option.tokens_amount}✨ за {option.price}₽",
                callback_data=Callbacks.BuyOptionSelectionCallback(option_index=indx),
            )
        builder.button(
            text="Назад",
            callback_data="buy_options_back",
        )
        builder.adjust(1)
        return builder.as_markup()


class AiogramMessageService(MessageService):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def _send_message(
        self,
        ctx: MessageContext,
        text: str,
        markup: InlineKeyboardMarkup | None = None,
        *args,
        **kwargs,
    ) -> MessageContext:
        if ctx.message_id:
            await self.bot.edit_message_text(
                text,
                chat_id=ctx.user.telegram_id,
                message_id=ctx.message_id,
                reply_markup=markup,
            )
            message_id = ctx.message_id
        else:
            message = await self.bot.send_message(
                chat_id=ctx.user.telegram_id, text=text, reply_markup=markup
            )
            message_id = message.message_id

        return MessageContext(ctx.user, message_id)

    async def delete_message(self, ctx: MessageContext):
        await self.bot.delete_message(ctx.user.telegram_id, ctx.message_id)

    async def send_resolution(self, ctx: MessageContext, resolution: str):
        """Текст модели не доверенный: лишние символы разметки и длина больше
        4096 иначе обрывают отправку ответа, за который уже заплачено."""
        sent = None
        for chunk in split_message(resolution):
            sent = await self._send_message(ctx, to_telegram_html(chunk))
        return sent

    async def send_balance_menu(self, ctx: MessageContext, formula: str):
        text = Texts.BALANCE_INFO.format(balance=ctx.user.bal, formula=formula)
        return await self._send_message(ctx, text, Keyboards.balance_menu())

    async def send_defendant_selection(
        self, ctx: MessageContext, variants: List[Speaker]
    ):
        markup = Keyboards.defendant_selection(variants)
        await self._send_message(ctx, text=Texts.DEFENDANT_SELECTION, markup=markup)

    async def send_prices_menu(self, ctx: MessageContext, options: List[BuyOption]):
        markup = Keyboards.buy_options(options)
        await self._send_message(ctx, text=Texts.PRICES_MENU_TITLE, markup=markup)
