import pytest

from src.application import Go, Session
from src.domain.models import User
from tests.mocks import MockMessageService, MockContextService
from tests.scenarios.add_messages import AddMessages
from tests.utils.factories import EventContextFactory, TestSessionFactory


class BaseTestGroup:
    async def add_messages(
        self, session: Session, count: int = 9, media_duration: int = 0
    ):
        await AddMessages(session, self.container.config.app_config()).execute(
            count, media_duration
        )

    @pytest.fixture(autouse=True)
    def setup_mocks(self, container):
        self.container = container

    @pytest.fixture(scope="function")
    def user(self):
        return User(telegram_id=1, id=1, bal=1000)

    @pytest.fixture(scope="function")
    def session(self, user):
        message_service = MockMessageService()
        context_service = MockContextService()
        session = TestSessionFactory(
            message_service=message_service,
            context_service=context_service,
            event=EventContextFactory(user=user),
        )
        return session

    @pytest.fixture
    def go_uc(self, session):
        return Go(
            session,
            self.container.core.dispute_resolver(),
            self.container.core.billing_service(),
            self.container.core.argue_service(),
        )
