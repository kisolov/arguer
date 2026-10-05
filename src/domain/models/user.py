from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class User:
    telegram_id: int
    id: int = field(default=None, metadata={"ignore": True})
    bal: Decimal = Decimal("150.00")
