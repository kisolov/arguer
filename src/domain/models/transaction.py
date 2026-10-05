import enum
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.domain.models import User

class TransactionStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELED = "canceled"


class TransactionCategory(enum.Enum):
    TOP_UP = "top_up"
    USAGE = "usage"
    REFUND = "refund"

@dataclass
class Transaction:
    user: User = field(metadata={"ignore": True})
    category: TransactionCategory
    amount: Decimal
    status: TransactionStatus = TransactionStatus.PENDING
    id: Optional[int] = None
    uuid: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)