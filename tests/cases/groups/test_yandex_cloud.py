from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.domain.ports import SpeechRecognitionError
from src.infrastructure import S3ClientSettings, YandexBucket, YandexSpeechKit
from tests.cases.base import BaseTestGroup


@pytest.fixture
def s3_settings():
    return S3ClientSettings(
        bucket_name="bucket",
        access_key_id="key",
        secret_access_key="secret",
        endpoint_url="https://storage.example",
    )


class TestYandexBucket(BaseTestGroup):
    @pytest.fixture
    def s3(self):
        return Mock()

    @pytest.fixture
    def bucket(self, s3_settings, s3):
        with patch("boto3.client", return_value=s3) as factory:
            self.factory = factory
            yield YandexBucket(s3_settings)

    @pytest.mark.asyncio
    async def test_client_uses_endpoint_and_credentials(self, bucket, s3):
        s3.list_objects_v2.return_value = {}

        await bucket.list_objects()

        kwargs = self.factory.call_args.kwargs
        assert kwargs["endpoint_url"] == "https://storage.example"
        assert kwargs["aws_access_key_id"] == "key"
        assert kwargs["aws_secret_access_key"] == "secret"

    @pytest.mark.asyncio
    async def test_upload_bytes_targets_bucket_and_key(self, bucket, s3):
        assert await bucket.upload_bytes(b"data", "a/b.ogg") is True

        _, bucket_name, key = s3.upload_fileobj.call_args.args
        assert (bucket_name, key) == ("bucket", "a/b.ogg")

    @pytest.mark.asyncio
    async def test_download_bytes_returns_written_content(self, bucket, s3):
        s3.download_fileobj.side_effect = lambda _b, _k, stream: stream.write(b"xyz")

        assert await bucket.download_bytes("a.ogg") == b"xyz"

    @pytest.mark.asyncio
    async def test_list_objects_returns_keys_and_handles_empty_bucket(
        self, bucket, s3
    ):
        s3.list_objects_v2.return_value = {"Contents": [{"Key": "a"}, {"Key": "b"}]}
        assert await bucket.list_objects("p/") == ["a", "b"]
        assert s3.list_objects_v2.call_args.kwargs == {"Bucket": "bucket", "Prefix": "p/"}

        s3.list_objects_v2.return_value = {}
        assert await bucket.list_objects() == []

    @pytest.mark.asyncio
    async def test_delete_and_presigned_url(self, bucket, s3):
        s3.generate_presigned_url.return_value = "https://signed"

        assert await bucket.delete_object("a") is True
        assert await bucket.generate_presigned_url("a", 60) == "https://signed"

        s3.delete_object.assert_called_once_with(Bucket="bucket", Key="a")
        assert s3.generate_presigned_url.call_args.kwargs["ExpiresIn"] == 60

    @pytest.mark.asyncio
    async def test_provider_failure_is_wrapped_with_object_name(self, bucket, s3):
        s3.upload_fileobj.side_effect = RuntimeError("denied")

        with pytest.raises(Exception, match="a/b.ogg.*denied"):
            await bucket.upload_bytes(b"data", "a/b.ogg")


class TestYandexSpeechKit(BaseTestGroup):
    @pytest.fixture
    def bucket(self):
        return Mock(upload_bytes=AsyncMock(return_value=True))

    @pytest.fixture
    def kit(self, bucket):
        return YandexSpeechKit(
            self.container.config.yandex_config(), bucket, Mock(get_token=Mock(return_value="iam"))
        )

    @pytest.mark.asyncio
    async def test_audio_is_uploaded_and_public_uri_returned(self, kit, bucket):
        uri = await kit._prepare_and_upload_audio(b"data", "ogg")

        key = bucket.upload_bytes.await_args.args[1]
        assert key.startswith("speechkit/") and key.endswith(".ogg")
        assert uri == f"https://storage.yandexcloud.net/test/{key}"

    @pytest.mark.asyncio
    async def test_recognize_joins_recognized_chunks(self, kit):
        kit._start_recognition = AsyncMock(return_value="op-1")
        kit._wait_for_result = AsyncMock(
            return_value={
                "response": {
                    "chunks": [
                        {"alternatives": [{"text": "привет", "confidence": 0.9}]},
                        {"alternatives": [{"confidence": 0.1}]},
                        {"alternatives": [{"text": "мир"}]},
                    ]
                }
            }
        )

        assert await kit.recognize(b"audio") == "привет мир"

    @pytest.mark.asyncio
    async def test_recognize_can_return_segments(self, kit):
        kit._start_recognition = AsyncMock(return_value="op-1")
        kit._wait_for_result = AsyncMock(
            return_value={
                "response": {"chunks": [{"alternatives": [{"text": "привет"}]}]}
            }
        )

        result = await kit.recognize(b"audio", join_results=False)

        assert result == [{"text": "привет", "confidence": 0}]

    @pytest.mark.asyncio
    async def test_any_failure_becomes_speech_recognition_error(self, kit, bucket):
        bucket.upload_bytes.side_effect = RuntimeError("s3 down")

        with pytest.raises(SpeechRecognitionError, match="s3 down"):
            await kit.recognize(b"audio")

    @pytest.mark.asyncio
    async def test_wait_for_result_times_out(self, kit):
        with pytest.raises(SpeechRecognitionError, match="timeout"):
            await kit._wait_for_result("op-1", timedelta(seconds=0))
