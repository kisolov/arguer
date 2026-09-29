from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.domain.exceptions import BusinessLogicError, UnexpectedError
from src.application import Session
from logs import logger


class ErrorHandlingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        session: Session,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(session, data)
        except BusinessLogicError as e:
            await session.message_service.send_error_message(
                session.answer_message_context, e
            )
        except Exception as e:
            logger.error(
                "Неожиданная ошибка",
                extra={"user_id": session.user.id, "exception": type(e).__name__},
                exc_info=True,
            )
            await session.message_service.send_error_message(
                session.answer_message_context, UnexpectedError()
            )
            await session.context_service.clear_data()
            await session.context_service.clear_state()
