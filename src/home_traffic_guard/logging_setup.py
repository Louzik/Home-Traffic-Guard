"""Вспомогательные функции настройки логирования."""

from __future__ import annotations

import logging
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_path: Path) -> None:
    """Настроить корневой логгер с консольным и файловым обработчиком с ротацией."""
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
    root_logger.addHandler(stream_handler)

    resolved_log_path = _resolve_log_path(log_path)
    try:
        file_handler = RotatingFileHandler(resolved_log_path, maxBytes=1_000_000, backupCount=3)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as error:
        root_logger.warning(
            "Не удалось инициализировать файловый лог '%s': %s. Продолжаем только с консольным логом.",
            resolved_log_path,
            error,
        )


def _resolve_log_path(log_path: Path) -> Path:
    """Проверить доступность каталога лога и при необходимости выбрать безопасный fallback."""
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return log_path
    except Exception:
        fallback_dir = Path(tempfile.gettempdir()) / "home_traffic_guard"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir / "home_traffic_guard.log"
