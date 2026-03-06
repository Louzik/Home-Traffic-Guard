"""Вспомогательные функции настройки логирования."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_path: Path) -> None:
    """Настроить корневой логгер с консольным и файловым обработчиком с ротацией."""
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)
