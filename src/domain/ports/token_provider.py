from typing import Protocol


class TokenProvider(Protocol):
    def create_token(self): ...
