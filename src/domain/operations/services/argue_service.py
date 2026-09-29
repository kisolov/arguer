import asyncio

from src.domain.models import Dialogue, Speaker, Argue, UnprocessedMessage, Reasoning
from src.domain.ports import MediaHandler


class ArgueService:
    def __init__(self, media_handler: MediaHandler):
        self.media_handler = media_handler

    async def create_from_dialogue(self, dialogue: Dialogue, defendant: Speaker):
        reasoning_list = await asyncio.gather(
            *[
                self._create_reasoning_from_unprocessed(unprocessed_msg)
                for unprocessed_msg in dialogue.messages
            ]
        )

        return Argue(reasoning_list, defendant)

    async def _create_reasoning_from_unprocessed(
        self, unprocessed_message: UnprocessedMessage
    ):
        text = unprocessed_message.text or await self._process_media(
            unprocessed_message.media
        )

        return Reasoning(content=text, speaker=unprocessed_message.speaker)

    async def _process_media(self, media) -> str:
        return await self.media_handler.get_media_as_text(media)
