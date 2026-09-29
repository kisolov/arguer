import factory
from uuid import uuid4

from src.domain.models import EventTypes, EventContext, User


class EventContextFactory(factory.Factory):
    class Meta:
        model = EventContext

    event_message_id = factory.Sequence(lambda n: n)
    event_id = factory.LazyAttribute(lambda _: str(uuid4()))
    data = None
    event_type = EventTypes.INCOMING_MESSAGE
    forward_from_name = None
    media = None
    user = factory.LazyAttribute(lambda _: User(telegram_id=1, id=1))
