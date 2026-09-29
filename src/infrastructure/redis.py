from typing import Optional, Any

import redis

from src.domain.ports.repositories.key_value_storage import KeyValueStorage


class RedisStorage(KeyValueStorage):
    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client

    def get(self, key: str) -> Optional[Any]:
        return self._redis.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if ttl:
            self._redis.setex(key, ttl, value)
        else:
            self._redis.set(key, value)

    def delete(self, key: str) -> None:
        self._redis.delete(key)

    def exists(self, key: str) -> bool:
        return bool(self._redis.exists(key))
