"""Модели конфигурации приложения."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    """Конфигурация выполнения Home Traffic Guard."""

    db_path: Path
    log_path: Path
    monitoring_interval_ms: int = 15000
    baseline_multiplier: float = 2.0

    @classmethod
    def default(cls) -> "AppConfig":
        """Создать пути конфигурации по умолчанию в домашнем каталоге пользователя."""
        app_dir = cls._resolve_app_dir()
        app_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            db_path=app_dir / "home_traffic_guard.sqlite3",
            log_path=app_dir / "home_traffic_guard.log",
        )

    @staticmethod
    def _resolve_app_dir() -> Path:
        """Определить рабочий каталог приложения с учетом платформы."""
        if os.name == "nt":
            local_app_data = os.getenv("LOCALAPPDATA")
            if local_app_data:
                return Path(local_app_data) / "HomeTrafficGuard"
        return Path.home() / ".home_traffic_guard"
