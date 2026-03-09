"""Заполнить БД небольшим демо-набором оповещений для проверки UI."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

from home_traffic_guard.config import AppConfig
from home_traffic_guard.db.connection import Database
from home_traffic_guard.db.repositories import AlertRepository, DeviceRepository
from home_traffic_guard.domain.models import Alert, Device


def _ensure_devices(device_repository: DeviceRepository) -> dict[str, int]:
    existing = device_repository.list_all()
    by_name = {item.name: item for item in existing}

    defaults = [
        ("WiFi Camera", "192.168.1.20", "AA:BB:CC:DD:EE:01"),
        ("Smart TV", "192.168.1.21", "AA:BB:CC:DD:EE:02"),
        ("Voice Assistant", "192.168.1.22", "AA:BB:CC:DD:EE:03"),
    ]

    for name, ip_address, mac_address in defaults:
        if name in by_name:
            continue
        created = device_repository.create(
            Device(
                id=None,
                name=name,
                ip_address=ip_address,
                mac_address=mac_address,
            )
        )
        by_name[name] = created

    return {name: int(item.id) for name, item in by_name.items() if item.id is not None}


def _seed_alerts(alert_repository: AlertRepository, device_ids: dict[str, int]) -> None:
    now = datetime.now()
    samples = [
        ("WiFi Camera", "high", "Резкий всплеск трафика на потоке камеры", 4, False),
        ("WiFi Camera", "high", "Повторяющийся исходящий всплеск на неизвестный хост", 11, True),
        ("Smart TV", "medium", "Неожиданный рост трафика в режиме ожидания", 19, False),
        ("Smart TV", "low", "Обнаружена новая multicast-активность", 31, True),
        ("Voice Assistant", "medium", "Частота DNS-запросов выше baseline", 46, False),
        ("Voice Assistant", "low", "Фоновая синхронизация выше обычного уровня", 63, False),
        ("WiFi Camera", "high", "Обнаружена крупная сессия исходящей передачи", 88, False),
        ("Smart TV", "medium", "Частые повторные подключения к облачному узлу", 121, True),
        ("Voice Assistant", "low", "Небольшое отклонение трафика в режиме простоя", 155, False),
    ]

    for device_name, severity, message, minutes_ago, acknowledged in samples:
        device_id = device_ids.get(device_name)
        if device_id is None:
            continue

        created_at = now - timedelta(minutes=minutes_ago)
        acknowledged_at = created_at + timedelta(minutes=3) if acknowledged else None
        alert_repository.create(
            Alert(
                id=None,
                device_id=device_id,
                severity=severity,
                message=message,
                created_at=created_at,
                acknowledged=acknowledged,
                acknowledged_at=acknowledged_at,
            )
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Сидирует небольшую демо-базу для таблицы оповещений.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Путь к SQLite БД. По умолчанию используется AppConfig.default().db_path",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    db_path = args.db_path or AppConfig.default().db_path
    database = Database(db_path)
    database.initialize()

    device_repository = DeviceRepository(database.connect)
    alert_repository = AlertRepository(database.connect)

    device_ids = _ensure_devices(device_repository)
    _seed_alerts(alert_repository, device_ids)

    print(f"Demo alerts inserted into: {db_path}")
    print("Open 'Оповещения' page to verify the table and filters.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
