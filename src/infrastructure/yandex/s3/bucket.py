import asyncio
import io
from typing import List, Optional, Any

import boto3
from botocore.client import Config

from .config import S3ClientSettings


class YandexBucket:
    def __init__(self, settings: S3ClientSettings):
        self.settings = settings

    def _create_s3_client(self) -> Any:
        """Создает и возвращает синхронный клиент S3."""
        try:
            return boto3.client(
                "s3",
                endpoint_url=self.settings.endpoint_url,
                aws_access_key_id=self.settings.access_key_id,
                aws_secret_access_key=self.settings.secret_access_key,
                config=Config(signature_version="s3v4"),
                # region_name=self.settings.yc_s3_region # Может понадобиться для некоторых операций или конфигураций
            )
        except Exception as e:
            # В реальном приложении здесь может быть более специфическая обработка
            raise Exception(f"Ошибка при создании клиента S3: {str(e)}")

    def _sync_upload_file(
        self, file_path: str, object_name: Optional[str] = None
    ) -> bool:
        s3 = self._create_s3_client()
        if object_name is None:
            object_name = file_path
        try:
            s3.upload_file(file_path, self.settings.bucket_name, object_name)
            return True
        except Exception as e:  # BotoCoreError, ClientError
            raise Exception(
                f"Ошибка загрузки файла {file_path} в {object_name}: {str(e)}"
            )

    async def upload_file(
        self, file_path: str, object_name: Optional[str] = None
    ) -> bool:
        """Асинхронно загружает файл в хранилище."""
        return await asyncio.to_thread(self._sync_upload_file, file_path, object_name)

    def _sync_download_file(
        self, object_name: str, file_path: Optional[str] = None
    ) -> bool:
        s3 = self._create_s3_client()
        if file_path is None:
            file_path = object_name
        try:
            s3.download_file(self.settings.bucket_name, object_name, file_path)
            return True
        except Exception as e:
            raise Exception(
                f"Ошибка скачивания файла {object_name} в {file_path}: {str(e)}"
            )

    async def download_file(
        self, object_name: str, file_path: Optional[str] = None
    ) -> bool:
        """Асинхронно скачивает файл из хранилища."""
        return await asyncio.to_thread(self._sync_download_file, object_name, file_path)

    def _sync_upload_bytes(self, bytes_data: bytes, object_name: str) -> bool:
        s3 = self._create_s3_client()
        try:
            with io.BytesIO(bytes_data) as data_stream:
                s3.upload_fileobj(data_stream, self.settings.bucket_name, object_name)
            return True
        except Exception as e:
            raise Exception(f"Ошибка загрузки байт в объект {object_name}: {str(e)}")

    async def upload_bytes(self, bytes_data: bytes, object_name: str) -> bool:
        """Асинхронно загружает бинарные данные в хранилище."""
        return await asyncio.to_thread(self._sync_upload_bytes, bytes_data, object_name)

    def _sync_download_bytes(self, object_name: str) -> bytes:
        s3 = self._create_s3_client()
        try:
            with io.BytesIO() as data_stream:
                s3.download_fileobj(self.settings.bucket_name, object_name, data_stream)
                return data_stream.getvalue()
        except Exception as e:
            raise Exception(
                f"Ошибка скачивания объекта {object_name} как байты: {str(e)}"
            )

    async def download_bytes(self, object_name: str) -> bytes:
        """Асинхронно получает файл в виде бинарных данных."""
        return await asyncio.to_thread(self._sync_download_bytes, object_name)

    def _sync_list_objects(self, prefix: str = "") -> List[str]:
        s3 = self._create_s3_client()
        try:
            response = s3.list_objects_v2(
                Bucket=self.settings.bucket_name, Prefix=prefix
            )
            return [obj["Key"] for obj in response.get("Contents", [])]
        except Exception as e:
            raise Exception(
                f"Ошибка получения списка объектов с префиксом '{prefix}': {str(e)}"
            )

    async def list_objects(self, prefix: str = "") -> List[str]:
        """Асинхронно получает список объектов в хранилище."""
        return await asyncio.to_thread(self._sync_list_objects, prefix)

    def _sync_delete_object(self, object_name: str) -> bool:
        s3 = self._create_s3_client()
        try:
            s3.delete_object(Bucket=self.settings.bucket_name, Key=object_name)
            return True
        except Exception as e:
            raise Exception(f"Ошибка удаления объекта {object_name}: {str(e)}")

    async def delete_object(self, object_name: str) -> bool:
        """Асинхронно удаляет объект из хранилища."""
        return await asyncio.to_thread(self._sync_delete_object, object_name)

    def _sync_generate_presigned_url(
        self, object_name: str, expiration: int = 3600
    ) -> str:
        s3 = self._create_s3_client()
        try:
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.settings.bucket_name, "Key": object_name},
                ExpiresIn=expiration,
            )
            return url
        except Exception as e:
            raise Exception(
                f"Ошибка генерации временной ссылки для {object_name}: {str(e)}"
            )

    async def generate_presigned_url(
        self, object_name: str, expiration: int = 3600
    ) -> str:
        """Асинхронно генерирует временную ссылку на объект."""
        return await asyncio.to_thread(
            self._sync_generate_presigned_url, object_name, expiration
        )
