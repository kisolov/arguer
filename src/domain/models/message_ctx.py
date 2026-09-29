from dataclasses import dataclass
from typing import Optional

from src.domain.models import User


@dataclass
class MessageContext:
    user: User
    message_id: Optional[int] = None