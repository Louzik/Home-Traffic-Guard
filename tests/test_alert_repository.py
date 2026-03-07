"""Тесты репозитория оповещений и миграции схемы."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from home_traffic_guard.db.connection import Database
from home_traffic_guard.db.repositories import AlertRepository, DeviceRepository
from home_traffic_guard.domain.models import Alert, Device


class AlertRepositoryTestCase(unittest.TestCase):
    """Проверяет подтверждение алертов и миграции поля acknowledged."""

    def setUp(self) -> None:
        self._db_file = Path(tempfile.gettempdir()) / f"htg_alert_repo_{id(self)}.sqlite3"
        if self._db_file.exists():
            self._db_file.unlink()

    def tearDown(self) -> None:
        if self._db_file.exists():
            self._db_file.unlink()

    def test_initialize_migrates_old_alerts_table(self) -> None:
        """Инициализация должна добавлять новые поля в старую таблицу alerts."""
        with sqlite3.connect(self._db_file) as connection:
            connection.execute(
                """
                CREATE TABLE alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

        database = Database(self._db_file)
        database.initialize()

        with database.connect() as connection:
            rows = connection.execute("PRAGMA table_info(alerts)").fetchall()
            columns = {str(row["name"]) for row in rows}

        self.assertIn("acknowledged", columns)
        self.assertIn("acknowledged_at", columns)

    def test_acknowledge_alert_roundtrip(self) -> None:
        """Подтверждение должно сохраняться в БД и читаться из list_recent."""
        database = Database(self._db_file)
        database.initialize()

        device_repository = DeviceRepository(database.connect)
        alert_repository = AlertRepository(database.connect)

        device = device_repository.create(
            Device(id=None, name="Device", ip_address="192.168.1.42", mac_address=None)
        )
        assert device.id is not None

        created = alert_repository.create(
            Alert(
                id=None,
                device_id=device.id,
                message="Alert",
                severity="high",
                created_at=datetime.now(),
            )
        )
        assert created.id is not None
        self.assertFalse(created.acknowledged)

        changed_at = datetime.now()
        alert_repository.set_acknowledged(created.id, acknowledged=True, changed_at=changed_at)

        recent = alert_repository.list_recent(limit=1)
        self.assertEqual(1, len(recent))
        self.assertTrue(recent[0].acknowledged)
        self.assertIsNotNone(recent[0].acknowledged_at)


if __name__ == "__main__":
    unittest.main()
