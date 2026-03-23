"""Модели конфигурации приложения."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import tempfile


@dataclass(slots=True)
class AppConfig:
    """Конфигурация выполнения Home Traffic Guard."""

    db_path: Path
    log_path: Path
    monitoring_interval_ms: int = 15000
    baseline_multiplier: float = 2.0
    demo_mode: bool = False

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
        preferred = Path.home() / ".home_traffic_guard"
        fallback = Path.home() / "Library" / "Application Support" / "HomeTrafficGuard"
        return AppConfig._first_writable_dir([preferred, fallback])

    @staticmethod
    def _first_writable_dir(candidates: list[Path]) -> Path:
        """Выбрать первый каталог, доступный для записи."""
        for candidate in candidates:
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                marker = candidate / ".write_test"
                marker.write_text("ok", encoding="utf-8")
                marker.unlink(missing_ok=True)
                return candidate
            except Exception:
                continue
        temp_dir = Path(tempfile.gettempdir()) / "home_traffic_guard"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir
