from datetime import timedelta

from logs import logger
from src.domain.ports import TokenProvider
from src.domain.operations import TokenService
from .base import UseCase


class RefreshToken(UseCase):
    # Вдвое чаще, чем истекает ключ в Redis: одно опоздавшее или упавшее
    # обновление не оставляет распознавание без токена
    INTERVAL = timedelta(minutes=30)

    def __init__(self, token_provider: TokenProvider, token_service: TokenService):
        self.provider = token_provider
        self.service = token_service

    def execute(self):
        try:
            token = self.provider.create_token()
        except Exception as ex:
            logger.error(f"Ошибка при получении токена: {ex}")
            raise
        self.service.save_token(token)
        logger.info("Токен обновлён")
