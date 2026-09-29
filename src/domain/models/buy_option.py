from dataclasses import dataclass


@dataclass
class BuyOption:
    tokens_amount: int
    price: int
    description: str