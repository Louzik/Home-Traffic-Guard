"""CLI-точка входа Home Traffic Guard."""

from __future__ import annotations

import argparse
import os

from home_traffic_guard.app import HomeTrafficGuardApp
from home_traffic_guard.config import AppConfig


def build_parser() -> argparse.ArgumentParser:
    """Создать CLI-парсер для параметров запуска."""
    parser = argparse.ArgumentParser(prog="home_traffic_guard")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Запустить приложение с демо-устройствами и демо-оповещениями.",
    )
    return parser


def _env_demo_enabled() -> bool:
    """Проверить, включен ли demo mode через переменную окружения."""
    value = os.getenv("HTG_DEMO_MODE", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def main() -> int:
    """Создать экземпляр приложения и запустить настольный интерфейс."""
    args = build_parser().parse_args()
    config = AppConfig.default()
    config.demo_mode = args.demo or _env_demo_enabled()
    app = HomeTrafficGuardApp(config)
    return app.run()
