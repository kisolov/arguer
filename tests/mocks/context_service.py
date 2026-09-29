from typing import Any, Dict

from src.domain.ports import ContextService
from tests.mocks.base import AutoMockMixin


class MockContextService(AutoMockMixin, ContextService):
    def __init__(self):
        self._storage = {}
        self._current_state = None
        super().__init__()

    async def get(self, key: str) -> Any:
        if key not in self._storage:
            raise KeyError(f"Key '{key}' not found")
        return self._storage[key]

    async def update(self, values: Dict[str, Any]) -> None:
        self._storage.update(values)

    async def set(self, values: Dict[str, Any]) -> None:
        self._storage = values.copy()

    async def clear_data(self) -> None:
        self._storage = {}

    async def clear_state(self) -> None:
        self._current_state = None

    async def set_processing_state(self) -> None:
        self._current_state = "processing"

    async def set_defendant_selection_state(self) -> None:
        self._current_state = "defendant_selection"
