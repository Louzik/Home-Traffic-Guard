"""CLI-точка входа Home Traffic Guard."""

from __future__ import annotations

from home_traffic_guard.app import HomeTrafficGuardApp
from home_traffic_guard.config import AppConfig


def main() -> int:
    """Создать экземпляр приложения и запустить настольный интерфейс."""
    config = AppConfig.default()
    app = HomeTrafficGuardApp(config)
    return app.run()
