import logging
import os
from logging.handlers import RotatingFileHandler, QueueListener, QueueHandler
from queue import Queue

log_format = "%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger(__name__)

log_dir = os.path.join(os.path.dirname(__file__), "log.log")
file_handler = RotatingFileHandler(
    log_dir, maxBytes=1000000, backupCount=5, encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter(log_format)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

log_queue = Queue()

queue_listener = QueueListener(log_queue, file_handler)
queue_listener.start()

queue_handler = QueueHandler(log_queue)
logger.addHandler(queue_handler)
