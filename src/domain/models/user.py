from dataclasses import dataclass, field


@dataclass
class User:
    telegram_id: int
    id: int = field(default=None, metadata={"ignore": True})
    bal: float = 150

