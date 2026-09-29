from apscheduler.schedulers.background import BackgroundScheduler
from datetime import timedelta
from typing import Callable, Any

from src.domain.ports import Scheduler


class CronScheduler(Scheduler):
    """Реализация планировщика на основе APScheduler."""

    def __init__(self):
        self._scheduler = BackgroundScheduler()
        self._scheduler.start()
        self._tasks = {}

    def schedule_every(
        self, interval: timedelta, task: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> str:
        job = self._scheduler.add_job(
            task, "interval", seconds=interval.total_seconds(), args=args, **kwargs
        )
        self._tasks[job.id] = job
        return job.id

    def stop(self, task_id: str) -> None:
        if task_id in self._tasks:
            self._tasks[task_id].remove()
            del self._tasks[task_id]
