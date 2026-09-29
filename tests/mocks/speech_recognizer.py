from typing import Any, Dict, List
from datetime import timedelta

from src.domain.ports import SpeechRecognitionInterface, SpeechRecognitionError


class MockSpeechRecognition(SpeechRecognitionInterface):
    def __init__(self):
        self._call_history = []

    async def recognize(
        self,
        audio_data: bytes,
        language_code: str = "ru-RU",
        audio_format: str = "ogg",
        join_results: bool = True,
        timeout: timedelta = timedelta(seconds=300),
        **kwargs
    ):
        self._call_history.append(
            {
                "audio_data": audio_data,
                "language_code": language_code,
                "audio_format": audio_format,
                "join_results": join_results,
                "timeout": timeout,
                "kwargs": kwargs,
            }
        )

        # По умолчанию возвращаем успешное распознавание
        return "Распознанный текст по умолчанию"

    # Методы для настройки поведения в тестах
    def set_success_response(
        self, text: str = None, chunks: List[Dict[str, Any]] = None
    ):
        """Настроить успешный ответ"""
        self.recognize_impl = lambda **kwargs: (
            chunks if chunks else text or "Успешно распознанный текст"
        )
        return self

    def set_error_response(self, error_message: str = "Ошибка распознавания"):
        """Настроить ответ с ошибкой"""
        self.recognize_impl = lambda **kwargs: (_ for _ in ()).throw(
            SpeechRecognitionError(error_message)
        )
        return self

    def get_call_history(self):
        return self._call_history.copy()

    def clear_history(self):
        self._call_history.clear()
