import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Union

import aiohttp

from config import YandexConfig
from src.domain.operations import TokenService
from src.domain.ports import (
    SpeechRecognitionInterface,
    SpeechRecognitionError,
)
from .bucket import YandexBucket


class YandexSpeechKit(SpeechRecognitionInterface):
    def __init__(
        self, settings: YandexConfig, bucket: YandexBucket, iam_repo: TokenService
    ):
        self.settings = settings
        self.bucket = bucket
        self.iam_repo = iam_repo

    async def _prepare_and_upload_audio(self, audio_data: bytes, extension: str) -> str:
        """Внутренний метод для загрузки аудио в S3"""
        content_type_map = {
            "ogg": "audio/ogg",
            "opus": "audio/opus",
            "wav": "audio/wav",
            "pcm": "audio/l16",
            "mp3": "audio/mpeg",
        }
        content_type = content_type_map.get(
            extension.lower(), "application/octet-stream"
        )
        object_key = (
            f"speechkit/{datetime.now().strftime('%Y%m%d')}/{uuid.uuid4()}.{extension}"
        )

        await self.bucket.upload_bytes(audio_data, object_key)
        return (
            f"https://storage.yandexcloud.net/{self.settings.bucket_name}/{object_key}"
        )

    async def recognize(
        self,
        audio_data: bytes,
        language_code: str = "ru-RU",
        audio_format: str = "ogg",
        join_results: bool = True,
        timeout: timedelta = timedelta(seconds=300),
        **kwargs,
    ) -> Union[str, List[Dict[str, Any]]]:
        """Основной метод распознавания"""
        try:
            # 1. Загрузка аудио
            audio_uri = await self._prepare_and_upload_audio(audio_data, audio_format)

            # 2. Конфигурация распознавания
            config = {
                "specification": {
                    "languageCode": language_code,
                    "audioEncoding": "OGG_OPUS",
                    "sampleRateHertz": 48000,
                    **{k: v for k, v in kwargs.items() if v is not None},
                }
            }

            # 3. Запуск распознавания
            operation_id = await self._start_recognition(audio_uri, config)

            # 4. Ожидание результата
            result = await self._wait_for_result(operation_id, timeout)

            # 5. Обработка результата
            chunks = []
            for chunk in result["response"].get("chunks", []):
                for alt in chunk.get("alternatives", []):
                    if "text" in alt:
                        chunks.append(
                            {
                                "text": alt["text"],
                                "confidence": alt.get("confidence", 0),
                            }
                        )

            return " ".join(c["text"] for c in chunks) if join_results else chunks

        except Exception as e:
            raise SpeechRecognitionError(f"Recognition failed: {str(e)}")

    async def _start_recognition(self, audio_uri: str, config: Dict[str, Any]) -> str:
        """Запуск операции распознавания"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.settings.stt_api_url,
                json={"audio": {"uri": audio_uri}, "config": {"specification": config}},
                headers={
                    "Authorization": f"Bearer {self.iam_repo.get_token()}",
                    "Content-Type": "application/json",
                },
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    raise SpeechRecognitionError(f"API error: {error}")
                return (await resp.json())["id"]

    async def _wait_for_result(
        self, operation_id: str, timeout: timedelta
    ) -> Dict[str, Any]:
        """Ожидание результата распознавания"""
        start_time = datetime.now()
        poll_interval = timedelta(seconds=5)

        while datetime.now() - start_time < timeout:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.settings.operation_api_url.rstrip('/')}/{operation_id}",
                    headers={"Authorization": f"Bearer {self.iam_repo.get_token()}"},
                ) as resp:
                    if resp.status != 200:
                        error = await resp.text()
                        raise SpeechRecognitionError(f"API error: {error}")

                    result = await resp.json()
                    if result.get("done"):
                        if "error" in result:
                            raise SpeechRecognitionError(result["error"])
                        if "response" not in result:
                            raise SpeechRecognitionError("No response in result")
                        return result

            await asyncio.sleep(poll_interval.total_seconds())

        raise SpeechRecognitionError("Recognition timeout")
