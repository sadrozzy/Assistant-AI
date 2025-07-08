import logging
from app.config import settings
from rich.logging import RichHandler
import os
import threading

_LOGGER = None


def logger(name: str = "assistant-ai") -> logging.Logger:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    if settings.DEBUG:
        log_format = "[%(asctime)s] | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
    else:
        log_format = "[%(asctime)s] | %(levelname)s | %(name)s | %(message)s"

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    handler = RichHandler(
        rich_tracebacks=True,
        show_time=False,
        show_level=False,
        show_path=False,
        markup=True,
    )
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(handler)
    logger.propagate = False
    _LOGGER = logger
    return logger
