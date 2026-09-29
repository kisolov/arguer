from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

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


class TestYandexBucketRemainingOperations(BaseTestGroup):
    @pytest.fixture
    def s3(self):
        return Mock()

    @pytest.fixture
    def bucket(self, s3_settings, s3):
        with patch("boto3.client", return_value=s3):
            yield YandexBucket(s3_settings)

    @pytest.mark.asyncio
    async def test_file_upload_and_download_default_to_same_name(self, bucket, s3):
        assert await bucket.upload_file("local.ogg") is True
        assert await bucket.download_file("remote.ogg") is True

        s3.upload_file.assert_called_once_with("local.ogg", "bucket", "local.ogg")
        s3.download_file.assert_called_once_with("bucket", "remote.ogg", "remote.ogg")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method, args, failing",
        [
            ("upload_file", ("a",), "upload_file"),
            ("download_file", ("a",), "download_file"),
            ("download_bytes", ("a",), "download_fileobj"),
            ("list_objects", (), "list_objects_v2"),
            ("delete_object", ("a",), "delete_object"),
            ("generate_presigned_url", ("a",), "generate_presigned_url"),
        ],
    )
    async def test_provider_failures_are_wrapped(
        self, bucket, s3, method, args, failing
    ):
        getattr(s3, failing).side_effect = RuntimeError("denied")

        with pytest.raises(Exception, match="denied"):
            await getattr(bucket, method)(*args)

    @pytest.mark.asyncio
    async def test_client_creation_failure_is_wrapped(self, s3_settings):
        with patch("boto3.client", side_effect=ValueError("bad endpoint")):
            with pytest.raises(Exception, match="bad endpoint"):
                await YandexBucket(s3_settings).list_objects()


def fake_http(json_body=None, status=200, text=""):
    """aiohttp.ClientSession, отвечающая одним заготовленным ответом."""
    response = Mock(status=status)
    response.json = AsyncMock(return_value=json_body)
    response.text = AsyncMock(return_value=text)
    request = MagicMock()
    request.__aenter__ = AsyncMock(return_value=response)
    request.__aexit__ = AsyncMock(return_value=False)
    session = MagicMock()
    session.post.return_value = request
    session.get.return_value = request
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, session


class TestSpeechKitHttp(BaseTestGroup):
    @pytest.fixture
    def kit(self):
        return YandexSpeechKit(
            self.container.config.yandex_config(),
            Mock(),
            Mock(get_token=Mock(return_value="iam")),
        )

    @pytest.mark.asyncio
    async def test_start_returns_operation_id_and_authorizes_with_iam(self, kit):
        ctx, session = fake_http({"id": "op-1"})

        with patch("aiohttp.ClientSession", return_value=ctx):
            assert await kit._start_recognition("https://audio", {}) == "op-1"

        headers = session.post.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer iam"

    @pytest.mark.asyncio
    async def test_start_http_error_is_reported(self, kit):
        ctx, _ = fake_http(status=403, text="forbidden")

        with patch("aiohttp.ClientSession", return_value=ctx):
            with pytest.raises(SpeechRecognitionError, match="forbidden"):
                await kit._start_recognition("https://audio", {})

    @pytest.mark.asyncio
    async def test_wait_returns_finished_operation(self, kit):
        done = {"done": True, "response": {"chunks": []}}
        ctx, session = fake_http(done)

        with patch("aiohttp.ClientSession", return_value=ctx):
            result = await kit._wait_for_result("op-1", timedelta(seconds=5))

        assert result == done
        assert session.get.call_args.args[0].endswith("/op-1")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "body, status, match",
        [
            ({"done": True, "error": "bad audio"}, 200, "bad audio"),
            ({"done": True}, 200, "No response"),
            (None, 500, "API error"),
        ],
    )
    async def test_wait_reports_failed_operations(self, kit, body, status, match):
        ctx, _ = fake_http(body, status=status, text="API error")

        with patch("aiohttp.ClientSession", return_value=ctx):
            with pytest.raises(SpeechRecognitionError, match=match):
                await kit._wait_for_result("op-1", timedelta(seconds=5))

    @pytest.mark.asyncio
    async def test_wait_polls_until_done(self, kit):
        pending_ctx, _ = fake_http({"done": False})
        done_ctx, _ = fake_http({"done": True, "response": {}})

        with patch("aiohttp.ClientSession", side_effect=[pending_ctx, done_ctx]):
            with patch("asyncio.sleep", new=AsyncMock()) as sleep:
                await kit._wait_for_result("op-1", timedelta(seconds=60))

        sleep.assert_awaited_once()
