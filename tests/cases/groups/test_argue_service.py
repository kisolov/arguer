import pytest

from src.domain.models import Dialogue, Media, Speaker, UnprocessedMessage
from tests.cases.base import BaseTestGroup


class TestArgueService(BaseTestGroup):
    @pytest.fixture
    def service(self):
        return self.container.core.argue_service()

    @pytest.mark.asyncio
    async def test_text_message_is_kept_as_is(self, service):
        dialogue = Dialogue([UnprocessedMessage(Speaker("a"), text="привет")])

        argue = await service.create_from_dialogue(dialogue, Speaker("a"))

        assert [(r.content, r.speaker) for r in argue.reasoning_list] == [
            ("привет", Speaker("a"))
        ]
        assert argue.defendant == Speaker("a")

    @pytest.mark.asyncio
    async def test_media_message_is_transcribed(self, service):
        dialogue = Dialogue(
            [UnprocessedMessage(Speaker("b"), media=Media("voice.ogg", 5))]
        )

        argue = await service.create_from_dialogue(dialogue, Speaker("a"))

        assert argue.reasoning_list[0].content == "Текст из медиа"
        assert argue.reasoning_list[0].speaker == Speaker("b")

    @pytest.mark.asyncio
    async def test_text_wins_over_media_when_both_present(self, service):
        dialogue = Dialogue(
            [
                UnprocessedMessage(
                    Speaker("a"), text="подпись", media=Media("voice.ogg", 5)
                )
            ]
        )

        argue = await service.create_from_dialogue(dialogue, Speaker("a"))

        assert argue.reasoning_list[0].content == "подпись"

    @pytest.mark.asyncio
    async def test_message_order_is_preserved(self, service):
        dialogue = Dialogue(
            [UnprocessedMessage(Speaker("a"), text=str(i)) for i in range(5)]
        )

        argue = await service.create_from_dialogue(dialogue, Speaker("a"))

        assert [r.content for r in argue.reasoning_list] == ["0", "1", "2", "3", "4"]
