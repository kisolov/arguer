import pytest

from src.domain.models import (
    Argue,
    Dialogue,
    Media,
    Reasoning,
    Speaker,
    UnprocessedMessage,
)
from tests.cases.base import BaseTestGroup


class TestSpeaker(BaseTestGroup):
    def test_speakers_with_same_name_are_equal(self):
        assert Speaker("a") == Speaker("a")
        assert hash(Speaker("a")) == hash(Speaker("a"))

    def test_speaker_is_not_equal_to_plain_string(self):
        assert Speaker("a") != "a"

    def test_speaker_is_usable_in_set(self):
        assert len({Speaker("a"), Speaker("a"), Speaker("b")}) == 2


class TestDialogue(BaseTestGroup):
    @pytest.fixture
    def dialogue(self):
        return Dialogue(
            [
                UnprocessedMessage(Speaker("a"), text="привет"),
                UnprocessedMessage(Speaker("b"), media=Media("x.ogg", 7)),
                UnprocessedMessage(Speaker("a"), text="ок", media=Media("y.ogg", 3)),
            ]
        )

    def test_participants_are_unique(self, dialogue):
        assert sorted(p.name for p in dialogue.partipitians) == ["a", "b"]

    def test_media_duration_sums_only_messages_with_media(self, dialogue):
        assert dialogue.media_duration == 10

    def test_total_symbols_counts_only_text(self, dialogue):
        assert dialogue.total_symbols == len("привет") + len("ок")

    def test_add_message_appends(self):
        dialogue = Dialogue()
        message = UnprocessedMessage(Speaker("a"), text="hi")

        dialogue.add_message(message)

        assert dialogue.messages == [message]

    def test_empty_dialogue_has_zero_totals(self):
        dialogue = Dialogue()

        assert dialogue.media_duration == 0
        assert dialogue.total_symbols == 0
        assert dialogue.partipitians == []

    def test_instances_do_not_share_message_list(self):
        first, second = Dialogue(), Dialogue()

        first.add_message(UnprocessedMessage(Speaker("a"), text="hi"))

        assert second.messages == []


class TestArgue(BaseTestGroup):
    def test_total_symbols_sums_reasoning_lengths(self):
        argue = Argue([Reasoning("abc", Speaker("a")), Reasoning("de", Speaker("b"))], Speaker("a"))

        assert argue.total_symbols == 5

    def test_add_reasoning_appends(self):
        argue = Argue([], Speaker("a"))

        argue.add_reasoning(Reasoning("x", Speaker("a")))

        assert [r.content for r in argue.reasoning_list] == ["x"]

    def test_add_resolution_is_recorded_as_assistant(self):
        argue = Argue([], Speaker("a"))

        argue.add_resolution("итог")

        assert argue.reasoning_list == [Reasoning("итог", Speaker("assistant"))]

    def test_add_concatenates_and_keeps_left_defendant(self):
        left = Argue([Reasoning("1", Speaker("a"))], Speaker("a"))
        right = Argue([Reasoning("2", Speaker("b"))], Speaker("b"))

        combined = left + right

        assert [r.content for r in combined.reasoning_list] == ["1", "2"]
        assert combined.defendant == Speaker("a")

    def test_add_does_not_mutate_operands(self):
        left = Argue([Reasoning("1", Speaker("a"))], Speaker("a"))
        right = Argue([Reasoning("2", Speaker("a"))], Speaker("a"))

        left + right

        assert len(left.reasoning_list) == 1
        assert len(right.reasoning_list) == 1

    def test_add_with_foreign_type_is_not_supported(self):
        with pytest.raises(NotImplementedError):
            Argue([], Speaker("a")) + 1
