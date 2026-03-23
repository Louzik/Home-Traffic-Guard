"""Тесты CRUD-операций для устройств."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from home_traffic_guard.db.connection import Database
from home_traffic_guard.db.repositories import DeviceRepository
from home_traffic_guard.domain.models import Device


class DeviceRepositoryTestCase(unittest.TestCase):
    """Проверяет создание, обновление и удаление устройств."""

    def setUp(self) -> None:
        self._db_file = Path(tempfile.gettempdir()) / f"htg_device_repo_{id(self)}.sqlite3"
        if self._db_file.exists():
            self._db_file.unlink()

        database = Database(self._db_file)
        database.initialize()
        self.device_repository = DeviceRepository(database.connect)

    def tearDown(self) -> None:
        if self._db_file.exists():
            self._db_file.unlink()

    def test_device_can_be_updated(self) -> None:
        """Устройство должно обновляться по id."""
        created = self.device_repository.create(
            Device(id=None, name="Old", ip_address="192.168.1.10", mac_address=None)
        )
        assert created.id is not None

        self.device_repository.update(
            Device(
                id=created.id,
                name="New",
                ip_address="192.168.1.20",
                mac_address="AA:BB:CC:DD:EE:FF",
            )
        )

        devices = self.device_repository.list_all()
        self.assertEqual(1, len(devices))
        self.assertEqual("New", devices[0].name)
        self.assertEqual("192.168.1.20", devices[0].ip_address)
        self.assertEqual("AA:BB:CC:DD:EE:FF", devices[0].mac_address)

    def test_device_can_be_deleted(self) -> None:
        """Устройство должно удаляться по id."""
        created = self.device_repository.create(
            Device(id=None, name="DeleteMe", ip_address="192.168.1.11", mac_address=None)
        )
        assert created.id is not None

        self.device_repository.delete(created.id)

        devices = self.device_repository.list_all()
        self.assertEqual([], devices)


if __name__ == "__main__":
    unittest.main()
