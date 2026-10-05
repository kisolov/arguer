import base64
import pickle
from typing import Any

from aiogram.fsm.storage.redis import RedisStorage as AiogramRedisStorage
from redis.asyncio import Redis


def dumps(data: Any) -> str:
    # В контексте лежат доменные объекты (Dialogue, Argue, Speaker), json их не умеет
    return base64.b64encode(pickle.dumps(data)).decode("ascii")


def loads(value: str) -> Any:
    return pickle.loads(base64.b64decode(value))


def create_fsm_storage(host: str, port: int) -> AiogramRedisStorage:
    """Контекст и состояния пользователей переживают перезапуск бота."""
    return AiogramRedisStorage(
        Redis(host=host, port=port), json_dumps=dumps, json_loads=loads
    )
