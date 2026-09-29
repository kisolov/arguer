from unittest.mock import AsyncMock
from abc import ABC


class AutoMockMixin(ABC):
    """Миксин для автоматического оборачивания методов в AsyncMock"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._async_mocks: dict[str, AsyncMock] = {}
        self._wrap_methods_with_async_mock()

    def _wrap_methods_with_async_mock(self):
        # ищем первый базовый класс, который является интерфейсом (ABC), а не сам миксин
        interface_class = next(
            base
            for base in self.__class__.__bases__
            if issubclass(base, ABC) and base is not AutoMockMixin
        )

        for method_name in dir(interface_class):
            if method_name.startswith("_"):
                continue

            method = getattr(self, method_name, None)
            if not callable(method):
                continue

            # создаём мок с делегированием на оригинал (если был)
            mock = AsyncMock(side_effect=method)
            self._async_mocks[method_name] = mock

            # подменяем атрибут на мок
            object.__setattr__(self, method_name, mock)

    def reset_mocks(self):
        """Сбрасывает все вызовы у AsyncMock'ов"""
        for mock in self._async_mocks.values():
            mock.reset_mock()
