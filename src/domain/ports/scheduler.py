from datetime import timedelta
from typing import Protocol, Callable, Any


class Scheduler(Protocol):
    def schedule_every(
        self, interval: timedelta, task: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> str:
        """Запускает задачу периодически с заданным интервалом."""
        pass

    def stop(self, task_id: str) -> None:
        """Останавливает задачу."""
        pass
