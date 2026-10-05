import json
import logging
import os
from logging.handlers import RotatingFileHandler, QueueListener, QueueHandler
from queue import Queue

log_format = "%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(message)s"

_STANDARD_ATTRS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"message", "asctime", "taskName"}


class ExtraFormatter(logging.Formatter):
    """Дописывает поля из `extra` к сообщению в виде JSON."""

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        extra = {k: v for k, v in record.__dict__.items() if k not in _STANDARD_ATTRS}
        if extra:
            line += " " + json.dumps(extra, ensure_ascii=False, default=str)
        return line


logging.basicConfig(level=logging.INFO)
for _handler in logging.getLogger().handlers:
    _handler.setFormatter(ExtraFormatter(log_format))
logger = logging.getLogger(__name__)

# В контейнере файл лежит в смонтированном каталоге, а не рядом с кодом
log_dir = os.getenv("LOG_FILE") or os.path.join(os.path.dirname(__file__), "log.log")
file_handler = RotatingFileHandler(
    log_dir, maxBytes=1000000, backupCount=5, encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(ExtraFormatter(log_format))

logger.addHandler(file_handler)

log_queue = Queue()

queue_listener = QueueListener(log_queue, file_handler)
queue_listener.start()

queue_handler = QueueHandler(log_queue)
logger.addHandler(queue_handler)
