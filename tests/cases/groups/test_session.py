from src.domain.models import MessageContext
from tests.cases.base import BaseTestGroup
from tests.utils.factories import TestSessionFactory


class TestSession(BaseTestGroup):
    def test_popup_is_allowed_only_for_button_sessions(self, session):
        assert session.popup_allowed is False
        assert TestSessionFactory(with_popup=True).popup_allowed is True

    def test_answer_context_targets_session_user_without_message(self, session):
        assert session.answer_message_context == MessageContext(session.user)
