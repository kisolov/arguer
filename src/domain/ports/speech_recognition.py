from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Union, List, Dict, Any


class SpeechRecognitionError(Exception):
    """Кастомное исключение для ошибок распознавания речи"""

    pass


class SpeechRecognitionInterface(ABC):
    @abstractmethod
    async def recognize(
        self,
        audio_data: bytes,
        language_code: str = "ru-RU",
        audio_format: str = "ogg",
        join_results: bool = True,
        timeout: timedelta = timedelta(seconds=300),
        **kwargs
    ) -> Union[str, List[Dict[str, Any]]]:
        """
        Распознает речь из аудиоданных.

        Args:
            audio_data: Байты аудиофайла
            language_code: Язык распознавания (например, "ru-RU")
            audio_format: Формат аудио (ogg, wav и т.д.)
            join_results: Если True - объединяет результаты в строку
            timeout: Максимальное время ожидания результата
            **kwargs: Дополнительные параметры распознавания

        Returns:
            str: объединенный текст (если join_results=True)
            List[Dict]: список сегментов с текстом и метаданными

        Raises:
            SpeechRecognitionError: при ошибках распознавания
        """
        raise NotImplementedError
