import asyncio
import io
import aiohttp
from pydub import AudioSegment
from logs import logger
from src.domain.models import Media
from src.domain.ports import MediaHandler, SpeechRecognitionInterface


class WebMediaHandler(MediaHandler):
    SUPPORTED_FORMATS = ["mp3", "wav", "ogg", "oga", "mp4"]
    AUDIO_FORMATS = ["mp3", "wav", "ogg", "oga"]

    def __init__(self, speech_recognizer: SpeechRecognitionInterface):
        self.speech_recognizer = speech_recognizer

    async def _get_url_file_extension(self, url: str) -> str:
        if not url:
            raise ValueError("URL not set")
        return url.split(".")[-1].lower()

    async def get_media_as_text(self, media: Media) -> str:
        url = media.url
        logger.info(f"Starting media processing for URL: {url}")

        try:
            extension = await self._get_url_file_extension(url)

            if extension not in self.SUPPORTED_FORMATS:
                error_msg = f"Файлы с расширением {extension} не поддерживаются"
                logger.error(error_msg)
                raise ValueError(error_msg)

            file_bytes = await self._download_file(url)

            if extension == "mp4":
                file_bytes = await self._convert_video_to_audio_bytes(file_bytes)

            return await self.speech_recognizer.recognize(file_bytes)

        except Exception as e:
            logger.error(f"Error processing media: {str(e)}", exc_info=True)
            raise

    async def _download_file(self, url: str) -> bytes:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        error_msg = f"Download failed: {response.status}"
                        logger.error(error_msg)
                        raise ValueError(error_msg)
                    return await response.read()
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)

    @staticmethod
    async def _convert_video_to_audio_bytes(video_bytes: bytes) -> bytes:
        # ffmpeg работает синхронно и долго: в event loop он остановил бы всех
        return await asyncio.to_thread(
            WebMediaHandler._convert_video_sync, video_bytes
        )

    @staticmethod
    def _convert_video_sync(video_bytes: bytes) -> bytes:
        try:
            with io.BytesIO(video_bytes) as video_stream:
                audio = AudioSegment.from_file(video_stream)
                with io.BytesIO() as ogg_stream:
                    audio.export(
                        ogg_stream, format="ogg", codec="libopus", bitrate="64k"
                    )
                    return ogg_stream.getvalue()
        except Exception as e:
            logger.error(f"Conversion failed: {str(e)}", exc_info=True)
            raise
