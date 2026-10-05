from typing import Optional

from src.domain.models import Token
from src.domain.ports.repositories import KeyValueStorage


class TokenService:
    def __init__(self, storage: KeyValueStorage, key_prefix: str = "auth_token"):
        self._storage = storage
        self._key_prefix = key_prefix

    def set_key_prefix(self, key_prefix: str):
        self._key_prefix = key_prefix

    def _get_full_key(self, token_id: str) -> str:
        return f"{self._key_prefix}:{token_id}"

    def get_token(self, token_id: str = "default") -> Optional[str]:
        """None, если токена нет: истёк TTL или его ещё не выпускали."""
        value = self._storage.get(self._get_full_key(token_id))
        return value.decode("utf-8") if value is not None else None

    def save_token(self, token: Token, token_id: str = "default") -> None:
        self._storage.set(
            key=self._get_full_key(token_id),
            value=token.value,
            ttl=token.lifetime_in_seconds,
        )

    def delete_token(self, token_id: str = "default") -> None:
        self._storage.delete(self._get_full_key(token_id))

    def token_exists(self, token_id: str = "default") -> bool:
        return self._storage.exists(self._get_full_key(token_id))
