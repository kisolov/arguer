from unittest.mock import Mock, patch

import pytest

from src.infrastructure import WebMediaHandler
from tests.cases.base import BaseTestGroup


class TestVideoConversion(BaseTestGroup):
    @pytest.mark.asyncio
    async def test_video_is_exported_as_opus_ogg(self):
        segment = Mock()
        segment.export.side_effect = lambda stream, **_: stream.write(b"ogg-bytes")

        with patch("src.infrastructure.web.AudioSegment") as audio:
            audio.from_file.return_value = segment
            result = await WebMediaHandler._convert_video_to_audio_bytes(b"video")

        assert result == b"ogg-bytes"
        assert segment.export.call_args.kwargs["format"] == "ogg"
        assert segment.export.call_args.kwargs["codec"] == "libopus"

    @pytest.mark.asyncio
    async def test_unreadable_video_propagates_error(self):
        with patch("src.infrastructure.web.AudioSegment") as audio:
            audio.from_file.side_effect = RuntimeError("not a video")
            with pytest.raises(RuntimeError, match="not a video"):
                await WebMediaHandler._convert_video_to_audio_bytes(b"junk")
