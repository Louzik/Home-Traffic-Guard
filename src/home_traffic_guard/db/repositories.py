"""Реализации репозиториев для сущностей базы данных."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Callable

from home_traffic_guard.domain.models import Alert, Device, TrafficSample


class DeviceRepository:
    """Репозиторий для операций с таблицей `devices`."""

    def __init__(self, connection_factory: Callable[[], sqlite3.Connection]) -> None:
        self._connection_factory = connection_factory

    def create(self, device: Device) -> Device:
        """Добавить устройство и вернуть сохраненную сущность с сгенерированным id."""
        with self._connection_factory() as connection:
            cursor = connection.execute(
                """
                INSERT INTO devices (name, ip_address, mac_address)
                VALUES (?, ?, ?)
                """,
                (device.name, device.ip_address, device.mac_address),
            )
            connection.commit()
            return Device(
                id=int(cursor.lastrowid),
                name=device.name,
                ip_address=device.ip_address,
                mac_address=device.mac_address,
                created_at=datetime.now(),
            )

    def list_all(self) -> list[Device]:
        """Вернуть все устройства, отсортированные по id."""
        with self._connection_factory() as connection:
            rows = connection.execute(
                "SELECT id, name, ip_address, mac_address, created_at FROM devices ORDER BY id"
            ).fetchall()

        return [
            Device(
                id=row["id"],
                name=row["name"],
                ip_address=row["ip_address"],
                mac_address=row["mac_address"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def update(self, device: Device) -> None:
        """Обновить существующее устройство."""
        if device.id is None:
            raise ValueError("device.id is required for update")

        with self._connection_factory() as connection:
            connection.execute(
                """
                UPDATE devices
                SET name = ?, ip_address = ?, mac_address = ?
                WHERE id = ?
                """,
                (device.name, device.ip_address, device.mac_address, device.id),
            )
            connection.commit()

    def delete(self, device_id: int) -> None:
        """Удалить устройство по id."""
        with self._connection_factory() as connection:
            connection.execute("DELETE FROM devices WHERE id = ?", (device_id,))
            connection.commit()


class TrafficSampleRepository:
    """Репозиторий для операций с таблицей `traffic_samples`."""

    def __init__(self, connection_factory: Callable[[], sqlite3.Connection]) -> None:
        self._connection_factory = connection_factory

    def add(self, sample: TrafficSample) -> TrafficSample:
        """Добавить измерение трафика и вернуть сохраненную сущность с id."""
        with self._connection_factory() as connection:
            cursor = connection.execute(
                """
                INSERT INTO traffic_samples (device_id, bytes_per_second, captured_at)
                VALUES (?, ?, ?)
                """,
                (
                    sample.device_id,
                    sample.bytes_per_second,
                    sample.captured_at.isoformat(timespec="seconds"),
                ),
            )
            connection.commit()
            return TrafficSample(
                id=int(cursor.lastrowid),
                device_id=sample.device_id,
                bytes_per_second=sample.bytes_per_second,
                captured_at=sample.captured_at,
            )

    def list_recent_values(self, device_id: int, limit: int = 30) -> list[float]:
        """Вернуть последние значения трафика устройства в порядке убывания времени."""
        with self._connection_factory() as connection:
            rows = connection.execute(
                """
                SELECT bytes_per_second
                FROM traffic_samples
                WHERE device_id = ?
                ORDER BY captured_at DESC
                LIMIT ?
                """,
                (device_id, limit),
            ).fetchall()

        return [float(row["bytes_per_second"]) for row in rows]

    def get_latest_sample(self, device_id: int) -> TrafficSample | None:
        """Вернуть последний сэмпл трафика для устройства или `None`."""
        with self._connection_factory() as connection:
            row = connection.execute(
                """
                SELECT id, device_id, bytes_per_second, captured_at
                FROM traffic_samples
                WHERE device_id = ?
                ORDER BY captured_at DESC
                LIMIT 1
                """,
                (device_id,),
            ).fetchone()

        if row is None:
            return None

        return TrafficSample(
            id=row["id"],
            device_id=row["device_id"],
            bytes_per_second=float(row["bytes_per_second"]),
            captured_at=datetime.fromisoformat(row["captured_at"]),
        )


class AlertRepository:
    """Репозиторий для операций с таблицей `alerts`."""

    def __init__(self, connection_factory: Callable[[], sqlite3.Connection]) -> None:
        self._connection_factory = connection_factory

    def create(self, alert: Alert) -> Alert:
        """Добавить оповещение и вернуть сохраненную сущность с id."""
        with self._connection_factory() as connection:
            cursor = connection.execute(
                """
                INSERT INTO alerts (device_id, message, severity, created_at, acknowledged, acknowledged_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    alert.device_id,
                    alert.message,
                    alert.severity,
                    alert.created_at.isoformat(timespec="seconds"),
                    1 if alert.acknowledged else 0,
                    alert.acknowledged_at.isoformat(timespec="seconds")
                    if alert.acknowledged_at is not None
                    else None,
                ),
            )
            connection.commit()
            return Alert(
                id=int(cursor.lastrowid),
                device_id=alert.device_id,
                message=alert.message,
                severity=alert.severity,
                created_at=alert.created_at,
                acknowledged=alert.acknowledged,
                acknowledged_at=alert.acknowledged_at,
            )

    def list_recent(self, limit: int = 50) -> list[Alert]:
        """Вернуть недавно созданные оповещения."""
        with self._connection_factory() as connection:
            rows = connection.execute(
                """
                SELECT id, device_id, message, severity, created_at, acknowledged, acknowledged_at
                FROM alerts
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            Alert(
                id=row["id"],
                device_id=row["device_id"],
                message=row["message"],
                severity=row["severity"],
                created_at=datetime.fromisoformat(row["created_at"]),
                acknowledged=bool(row["acknowledged"]),
                acknowledged_at=(
                    datetime.fromisoformat(row["acknowledged_at"])
                    if row["acknowledged_at"] is not None
                    else None
                ),
            )
            for row in rows
        ]

    def set_acknowledged(self, alert_id: int, acknowledged: bool, changed_at: datetime) -> None:
        """Изменить статус подтверждения оповещения."""
        with self._connection_factory() as connection:
            connection.execute(
                """
                UPDATE alerts
                SET acknowledged = ?,
                    acknowledged_at = ?
                WHERE id = ?
                """,
                (
                    1 if acknowledged else 0,
                    changed_at.isoformat(timespec="seconds") if acknowledged else None,
                    alert_id,
                ),
            )
            connection.commit()

    def count_since(self, since: datetime) -> int:
        """Вернуть количество оповещений, созданных с указанного момента времени."""
        with self._connection_factory() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM alerts
                WHERE created_at >= ?
                """,
                (since.isoformat(timespec="seconds"),),
            ).fetchone()

        if row is None:
            return 0
        return int(row["total"])
