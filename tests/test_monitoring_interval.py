"""Тесты изменения интервала мониторинга."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from home_traffic_guard.analytics.baseline import BaselineAnalyzer
from home_traffic_guard.collectors.models import CollectedTraffic
from home_traffic_guard.db.connection import Database
from home_traffic_guard.db.repositories import AlertRepository, DeviceRepository, TrafficSampleRepository
from home_traffic_guard.domain.models import Device
from home_traffic_guard.notifications.service import NotificationService
from home_traffic_guard.services.monitoring_service import MonitoringService


class CollectorWithWindow:
    """Тестовый коллектор, поддерживающий настройку окна агрегации."""

    def __init__(self) -> None:
        self.window_seconds: float | None = None

    def collect(self, devices: list[Device]) -> list[CollectedTraffic]:
        return []

    def set_window_seconds(self, window_seconds: float) -> None:
        self.window_seconds = window_seconds


class MonitoringIntervalTestCase(unittest.TestCase):
    """Проверяет изменение интервала мониторинга в рантайме."""

    def setUp(self) -> None:
        self._db_file = Path(tempfile.gettempdir()) / f"htg_interval_{id(self)}.sqlite3"
        if self._db_file.exists():
            self._db_file.unlink()

        database = Database(self._db_file)
        database.initialize()

        self.device_repository = DeviceRepository(database.connect)
        self.traffic_repository = TrafficSampleRepository(database.connect)
        self.alert_repository = AlertRepository(database.connect)

    def tearDown(self) -> None:
        if self._db_file.exists():
            self._db_file.unlink()

    def test_interval_can_be_updated_and_propagated_to_collector(self) -> None:
        """Интервал должен обновляться и передаваться в коллектор."""
        collector = CollectorWithWindow()
        service = MonitoringService(
            collector=collector,
            device_repository=self.device_repository,
            traffic_repository=self.traffic_repository,
            alert_repository=self.alert_repository,
            analyzer=BaselineAnalyzer(multiplier=2.0),
            notification_service=NotificationService(),
            interval_ms=15_000,
        )

        self.assertEqual(15_000, service.get_interval_ms())

        service.set_interval_ms(30_000)

        self.assertEqual(30_000, service.get_interval_ms())
        self.assertEqual(30.0, collector.window_seconds)

    def test_baseline_multiplier_can_be_updated(self) -> None:
        """Множитель baseline должен изменяться во время выполнения."""
        collector = CollectorWithWindow()
        service = MonitoringService(
            collector=collector,
            device_repository=self.device_repository,
            traffic_repository=self.traffic_repository,
            alert_repository=self.alert_repository,
            analyzer=BaselineAnalyzer(multiplier=2.0),
            notification_service=NotificationService(),
            interval_ms=15_000,
        )

        self.assertEqual(2.0, service.get_baseline_multiplier())

        service.set_baseline_multiplier(3.0)

        self.assertEqual(3.0, service.get_baseline_multiplier())


if __name__ == "__main__":
    unittest.main()
