"""Распознавание речи: верный запрос, чистый бакет, токен без блокировки event loop."""

import asyncio
import threading
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.application import RefreshToken
from src.domain.operations import TokenService
from src.domain.ports import SpeechRecognitionError
from src.infrastructure import WebMediaHandler, YandexSpeechKit
from src.infrastructure.yandex.cloud_cli import TOKEN_TTL_SECONDS
from tests.cases.base import BaseTestGroup
from tests.cases.groups.test_yandex_cloud_io import fake_http


class TestSpeechKitRequest(BaseTestGroup):
    @pytest.fixture
    def bucket(self):
        return Mock(upload_bytes=AsyncMock(), delete_object=AsyncMock())

    @pytest.fixture
    def tokens(self):
        return Mock(get_token=Mock(return_value="iam"))

    @pytest.fixture
    def kit(self, bucket, tokens):
        return YandexSpeechKit(self.container.config.yandex_config(), bucket, tokens)

    def finished(self, kit):
        kit._wait_for_result = AsyncMock(
            return_value={"response": {"chunks": [{"alternatives": [{"text": "да"}]}]}}
        )

    @pytest.mark.asyncio
    async def test_specification_is_not_nested_twice(self, kit):
        ctx, session = fake_http({"id": "op-1"})
        self.finished(kit)

        with patch("aiohttp.ClientSession", return_value=ctx):
            await kit.recognize(b"audio")

        config = session.post.call_args.kwargs["json"]["config"]
        assert config["specification"]["languageCode"] == "ru-RU"
        assert "specification" not in config["specification"]

    @pytest.mark.asyncio
    async def test_uploaded_audio_is_removed_after_success(self, kit, bucket):
        kit._start_recognition = AsyncMock(return_value="op-1")
        self.finished(kit)

        assert await kit.recognize(b"audio") == "да"

        key = bucket.upload_bytes.await_args.args[1]
        bucket.delete_object.assert_awaited_once_with(key)

    @pytest.mark.asyncio
    async def test_uploaded_audio_is_removed_after_failure(self, kit, bucket):
        kit._start_recognition = AsyncMock(side_effect=RuntimeError("stt down"))

        with pytest.raises(SpeechRecognitionError):
            await kit.recognize(b"audio")

        bucket.delete_object.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cleanup_failure_does_not_lose_result(self, kit, bucket):
        kit._start_recognition = AsyncMock(return_value="op-1")
        self.finished(kit)
        bucket.delete_object.side_effect = RuntimeError("s3 down")

        assert await kit.recognize(b"audio") == "да"

    @pytest.mark.asyncio
    async def test_nothing_to_remove_when_upload_failed(self, kit, bucket):
        bucket.upload_bytes.side_effect = RuntimeError("s3 down")

        with pytest.raises(SpeechRecognitionError):
            await kit.recognize(b"audio")

        bucket.delete_object.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_token_is_clear_error(self, kit, tokens):
        tokens.get_token.return_value = None

        with pytest.raises(SpeechRecognitionError, match="IAM"):
            await kit._start_recognition("https://audio", {})

    @pytest.mark.asyncio
    async def test_token_is_read_off_the_event_loop(self, kit, tokens):
        loop_thread = threading.get_ident()
        seen = []
        tokens.get_token.side_effect = lambda: seen.append(threading.get_ident()) or "iam"

        await kit._auth_header()

        assert seen and seen[0] != loop_thread


class TestTokenLifetime(BaseTestGroup):
    def test_missing_token_reads_as_none(self):
        storage = Mock(get=Mock(return_value=None))

        assert TokenService(storage).get_token() is None

    def test_refresh_leaves_margin_before_expiry(self):
        assert RefreshToken.INTERVAL * 2 <= timedelta(seconds=TOKEN_TTL_SECONDS)


class TestVideoConversionOffLoop(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_conversion_runs_in_worker_thread(self):
        loop_thread = threading.get_ident()
        seen = []

        def convert(video):
            seen.append(threading.get_ident())
            return b"ogg"

        with patch.object(WebMediaHandler, "_convert_video_sync", side_effect=convert):
            assert await WebMediaHandler._convert_video_to_audio_bytes(b"v") == b"ogg"

        assert seen and seen[0] != loop_thread

    @pytest.mark.asyncio
    async def test_loop_keeps_serving_during_conversion(self):
        release = threading.Event()

        def slow(video):
            release.wait(2)
            return b"ogg"

        with patch.object(WebMediaHandler, "_convert_video_sync", side_effect=slow):
            conversion = asyncio.create_task(
                WebMediaHandler._convert_video_to_audio_bytes(b"v")
            )
            await asyncio.sleep(0.01)  # loop не заблокирован: этот await вернулся
            assert not conversion.done()
            release.set()
            assert await conversion == b"ogg"
