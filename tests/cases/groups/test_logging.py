import json
import logging

from logs.logger import ExtraFormatter
from tests.cases.base import BaseTestGroup


def make_record(**extra):
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "Событие", (), None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


class TestExtraFormatter(BaseTestGroup):
    def test_record_without_extra_is_left_unchanged(self):
        assert ExtraFormatter("%(message)s").format(make_record()) == "Событие"

    def test_extra_is_appended_as_json(self):
        line = ExtraFormatter("%(message)s").format(make_record(user_id=7, symbols=120))

        message, payload = line.split(" ", 1)
        assert message == "Событие"
        assert json.loads(payload) == {"user_id": 7, "symbols": 120}

    def test_non_ascii_values_are_kept_readable(self):
        line = ExtraFormatter("%(message)s").format(make_record(name_="Аня"))

        assert "Аня" in line

    def test_unserializable_value_does_not_break_logging(self):
        line = ExtraFormatter("%(message)s").format(make_record(obj=object()))

        assert line.startswith("Событие {")
