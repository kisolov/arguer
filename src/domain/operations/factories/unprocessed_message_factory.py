from typing import Optional

from src.domain.models import Speaker, UnprocessedMessage, Media


class UnprocessedMessageFactory:
    def create(
        self,
        speaker_name: Optional[str] = "hidden",
        media: Optional[Media] = None,
        text: Optional[str] = None,
    ):
        if not media and not text:
            raise ValueError("Media url or text required")

        unprocessed_message = UnprocessedMessage(Speaker(speaker_name or "hidden"))
        unprocessed_message.media = media
        unprocessed_message.text = text

        return unprocessed_message
