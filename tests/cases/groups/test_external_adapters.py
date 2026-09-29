import subprocess
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.domain.exceptions import RecordNotFound
from src.domain.models import Media, TransactionStatus
from src.domain.ports import SpeechRecognitionError
from src.infrastructure import (
    CronScheduler,
    RedisStorage,
    WebMediaHandler,
    YCCLIWrapper,
    YooKassaGateway,
)
from src.infrastructure.memory import InMemoryBuyOptionsRepository
from tests.cases.base import BaseTestGroup
from tests.mocks import MockSpeechRecognition


class TestInMemoryBuyOptions(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_options_are_listed_and_addressable_by_index(self):
        repo = InMemoryBuyOptionsRepository()

        options = await repo.get_all()

        assert await repo.get(0) is options[0]
        assert len(options) == 4

    @pytest.mark.asyncio
    async def test_unknown_index_raises(self):
        with pytest.raises(RecordNotFound):
            await InMemoryBuyOptionsRepository().get(99)


class TestRedisStorage(BaseTestGroup):
    @pytest.fixture
    def redis(self):
        return Mock()

    @pytest.fixture
    def storage(self, redis):
        return RedisStorage(redis)

    def test_set_with_ttl_uses_setex(self, storage, redis):
        storage.set("k", "v", ttl=60)

        redis.setex.assert_called_once_with("k", 60, "v")
        redis.set.assert_not_called()

    def test_set_without_ttl_uses_plain_set(self, storage, redis):
        storage.set("k", "v")

        redis.set.assert_called_once_with("k", "v")

    def test_get_and_delete_are_delegated(self, storage, redis):
        redis.get.return_value = b"v"

        assert storage.get("k") == b"v"
        storage.delete("k")
        redis.delete.assert_called_once_with("k")

    def test_exists_is_coerced_to_bool(self, storage, redis):
        redis.exists.return_value = 1

        assert storage.exists("k") is True


class TestYCCLIWrapper(BaseTestGroup):
    def test_returns_stripped_token_with_one_hour_lifetime(self):
        completed = subprocess.CompletedProcess([], 0, stdout="t0ken\n", stderr="")

        with patch("subprocess.run", return_value=completed) as run:
            token = YCCLIWrapper("yc").create_token()

        assert (token.value, token.lifetime_in_seconds) == ("t0ken", 3600)
        assert run.call_args.args[0] == ["yc", "iam", "create-token"]

    def test_cli_failure_is_reported_with_stderr(self):
        error = subprocess.CalledProcessError(
            2, ["yc", "iam", "create-token"], output="", stderr="not authorized"
        )

        with patch("subprocess.run", side_effect=error):
            with pytest.raises(RuntimeError, match="not authorized"):
                YCCLIWrapper("yc").create_token()

    def test_missing_binary_is_wrapped(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("yc")):
            with pytest.raises(RuntimeError, match="Unexpected error"):
                YCCLIWrapper("yc").create_token()


class TestYooKassaGateway(BaseTestGroup):
    @pytest.fixture
    def gateway(self):
        return YooKassaGateway(self.container.config.yoo_config())

    @pytest.mark.asyncio
    async def test_create_payment_builds_redirect_request(self, gateway):
        response = Mock(id="pay-1")
        response.confirmation.confirmation_url = "https://pay/1"

        with patch("src.infrastructure.yookassa.YooClient") as client:
            client.create = Mock(return_value=response)
            info = await gateway.create_payment(20, "100✨")

        body, idempotence_key = client.create.call_args.args
        assert body["amount"] == {"value": "20.00", "currency": "RUB"}
        assert body["confirmation"]["type"] == "redirect"
        assert body["capture"] is True
        assert body["description"] == "100✨"
        assert idempotence_key
        assert (info.confirmation_url, info.payment_uuid) == ("https://pay/1", "pay-1")

    @pytest.mark.parametrize(
        "provider_status, expected",
        [
            ("pending", TransactionStatus.PENDING),
            ("waiting_for_capture", TransactionStatus.PENDING),
            ("succeeded", TransactionStatus.COMPLETED),
            ("canceled", TransactionStatus.CANCELED),
            ("something-new", TransactionStatus.PENDING),
        ],
    )
    @pytest.mark.asyncio
    async def test_status_mapping(self, gateway, provider_status, expected):
        with patch("src.infrastructure.yookassa.YooClient") as client:
            client.find_one = Mock(return_value=Mock(status=provider_status))
            assert await gateway.get_payment_status("pay-1") == expected


class TestCronScheduler(BaseTestGroup):
    def test_scheduled_job_can_be_stopped(self):
        scheduler = CronScheduler()
        try:
            job_id = scheduler.schedule_every(timedelta(hours=1), lambda: None)
            assert scheduler._scheduler.get_job(job_id) is not None

            scheduler.stop(job_id)

            assert scheduler._scheduler.get_job(job_id) is None
            scheduler.stop(job_id)  # повторная остановка безопасна
        finally:
            scheduler._scheduler.shutdown(wait=False)


class TestWebMediaHandler(BaseTestGroup):
    @pytest.fixture
    def recognizer(self):
        return MockSpeechRecognition()

    @pytest.fixture
    def handler(self, recognizer):
        handler = WebMediaHandler(recognizer)
        handler._download_file = AsyncMock(return_value=b"audio")
        return handler

    @pytest.mark.asyncio
    async def test_audio_is_downloaded_and_recognized(self, handler, recognizer):
        text = await handler.get_media_as_text(Media("https://x/voice.OGA", 3))

        handler._download_file.assert_awaited_once_with("https://x/voice.OGA")
        assert text == "Распознанный текст по умолчанию"
        assert recognizer.get_call_history()[0]["audio_data"] == b"audio"

    @pytest.mark.asyncio
    async def test_video_is_converted_before_recognition(self, handler, recognizer):
        handler._convert_video_to_audio_bytes = AsyncMock(return_value=b"converted")

        await handler.get_media_as_text(Media("https://x/note.mp4", 3))

        handler._convert_video_to_audio_bytes.assert_awaited_once_with(b"audio")
        assert recognizer.get_call_history()[0]["audio_data"] == b"converted"

    @pytest.mark.asyncio
    async def test_unsupported_extension_is_rejected_without_download(self, handler):
        with pytest.raises(ValueError, match="не поддерживаются"):
            await handler.get_media_as_text(Media("https://x/doc.pdf", 3))

        handler._download_file.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_empty_url_is_rejected(self, handler):
        with pytest.raises(ValueError, match="URL"):
            await handler.get_media_as_text(Media("", 3))

    @pytest.mark.asyncio
    async def test_recognition_failure_propagates(self, handler, recognizer):
        recognizer.recognize = AsyncMock(side_effect=SpeechRecognitionError("boom"))

        with pytest.raises(SpeechRecognitionError):
            await handler.get_media_as_text(Media("https://x/voice.ogg", 3))

    @pytest.mark.asyncio
    async def test_download_http_error_is_reported(self):
        handler = WebMediaHandler(MockSpeechRecognition())
        response = MagicMock(status=404)
        get_ctx = MagicMock()
        get_ctx.__aenter__ = AsyncMock(return_value=response)
        get_ctx.__aexit__ = AsyncMock(return_value=False)
        session = MagicMock()
        session.get.return_value = get_ctx
        session_ctx = MagicMock()
        session_ctx.__aenter__ = AsyncMock(return_value=session)
        session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=session_ctx):
            with pytest.raises(ValueError, match="404"):
                await handler._download_file("https://x/voice.ogg")
