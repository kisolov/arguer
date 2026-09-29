import enum
from dataclasses import dataclass
from typing import Optional, Any

from src.domain.models import User, Media

class EventTypes(enum.Enum):
    INCOMING_MESSAGE = "incoming_message"
    BUTTON_PRESSED = "button_pressed"

@dataclass
class EventContext:
    event_message_id: int
    data: Any
    user: User
    event_type: EventTypes
    event_id: int | str
    media: Optional[Media] = None
    forward_from_name: Optional[str] = None
