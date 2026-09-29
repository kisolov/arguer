from dataclasses import dataclass


@dataclass
class Token:
    value: str
    lifetime_in_seconds: int
