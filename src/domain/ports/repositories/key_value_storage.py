from typing import Protocol, Optional, Any


class KeyValueStorage(Protocol):
    def get(self, key: str) -> Optional[Any]:
        pass

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass

    def delete(self, key: str) -> None:
        pass

    def exists(self, key: str) -> bool:
        pass
