import pytest

from src.domain.models import Media, Speaker
from src.domain.operations import UnprocessedMessageFactory
from tests.cases.base import BaseTestGroup


class TestUnprocessedMessageFactory(BaseTestGroup):
    @pytest.fixture
    def factory(self):
        return UnprocessedMessageFactory()

    def test_creates_text_message(self, factory):
        message = factory.create("alice", text="привет")

        assert message.speaker == Speaker("alice")
        assert message.text == "привет"
        assert message.media is None

    def test_creates_media_message(self, factory):
        media = Media("v.ogg", 3)

        message = factory.create("alice", media=media)

        assert message.media is media
        assert message.text is None

    def test_speaker_defaults_to_hidden(self, factory):
        assert factory.create(text="hi").speaker == Speaker("hidden")

    def test_requires_text_or_media(self, factory):
        with pytest.raises(ValueError):
            factory.create("alice")
