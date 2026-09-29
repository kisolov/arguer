import factory

from src.application import Session
from .event_context_factory import EventContextFactory
from ...mocks import MockContextService, MockMessageService, MockPopupService


class TestSessionFactory(factory.Factory):
    class Meta:
        model = Session

    event = factory.SubFactory(EventContextFactory)
    context_service = factory.LazyAttribute(lambda _: MockContextService())
    message_service = factory.LazyAttribute(lambda _: MockMessageService())
    popup_service = None

    class Params:
        with_popup = factory.Trait(
            popup_service=factory.LazyAttribute(
                lambda _: MockPopupService("test_cq_id")
            )
        )
