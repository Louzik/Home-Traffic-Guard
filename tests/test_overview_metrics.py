"""Тесты метрик страницы обзора."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from home_traffic_guard.analytics.baseline import BaselineAnalyzer
from home_traffic_guard.collectors.dummy_collector import DummyTrafficCollector
from home_traffic_guard.db.connection import Database
from home_traffic_guard.db.repositories import AlertRepository, DeviceRepository, TrafficSampleRepository
from home_traffic_guard.domain.models import Alert, Device, TrafficSample
from home_traffic_guard.notifications.service import NotificationService
from home_traffic_guard.services.monitoring_service import MonitoringService


class OverviewMetricsTestCase(unittest.TestCase):
    """Проверяет агрегацию метрик на странице обзора."""

    def setUp(self) -> None:
        self._db_file = Path(tempfile.gettempdir()) / f"htg_overview_{id(self)}.sqlite3"
        if self._db_file.exists():
            self._db_file.unlink()

        database = Database(self._db_file)
        database.initialize()

        self.device_repository = DeviceRepository(database.connect)
        self.traffic_repository = TrafficSampleRepository(database.connect)
        self.alert_repository = AlertRepository(database.connect)

        self.monitoring_service = MonitoringService(
            collector=DummyTrafficCollector(),
            device_repository=self.device_repository,
            traffic_repository=self.traffic_repository,
            alert_repository=self.alert_repository,
            analyzer=BaselineAnalyzer(multiplier=2.0),
            notification_service=NotificationService(),
            interval_ms=3000,
        )

    def tearDown(self) -> None:
        if self._db_file.exists():
            self._db_file.unlink()

    def test_empty_metrics_without_samples(self) -> None:
        """Без сэмплов должны возвращаться нулевые значения."""
        metrics = self.monitoring_service.get_overview_metrics()

        self.assertEqual(0.0, metrics.total_speed_bps)
        self.assertEqual(0, metrics.active_devices)
        self.assertEqual(0, metrics.alerts_last_24h)
        self.assertIsNone(metrics.last_sample_at)

    def test_metrics_use_latest_samples_and_24h_alerts(self) -> None:
        """Метрики должны учитывать только последние сэмплы и алерты за 24 часа."""
        now = datetime.now()
        old_time = now - timedelta(minutes=2)

        device_a = self.device_repository.create(
            Device(id=None, name="A", ip_address="192.168.1.10", mac_address=None),
        )
        device_b = self.device_repository.create(
            Device(id=None, name="B", ip_address="192.168.1.11", mac_address=None),
        )

        assert device_a.id is not None
        assert device_b.id is not None

        self.traffic_repository.add(
            TrafficSample(
                id=None,
                device_id=device_a.id,
                bytes_per_second=1024.0,
                captured_at=now,
            )
        )
        self.traffic_repository.add(
            TrafficSample(
                id=None,
                device_id=device_b.id,
                bytes_per_second=2048.0,
                captured_at=old_time,
            )
        )
        self.alert_repository.create(
            Alert(
                id=None,
                device_id=device_a.id,
                message="recent",
                severity="high",
                created_at=now - timedelta(hours=2),
            )
        )
        self.alert_repository.create(
            Alert(
                id=None,
                device_id=device_a.id,
                message="old",
                severity="high",
                created_at=now - timedelta(hours=30),
            )
        )

        metrics = self.monitoring_service.get_overview_metrics()

        self.assertEqual(3072.0, metrics.total_speed_bps)
        self.assertEqual(1, metrics.active_devices)
        self.assertEqual(1, metrics.alerts_last_24h)
        self.assertIsNotNone(metrics.last_sample_at)

    def test_device_table_rows_include_risk(self) -> None:
        """Строки таблицы должны содержать последнюю скорость и оценку риска."""
        now = datetime.now()
        device = self.device_repository.create(
            Device(id=None, name="Sensor", ip_address="192.168.1.50", mac_address=None),
        )
        assert device.id is not None

        self.traffic_repository.add(
            TrafficSample(
                id=None,
                device_id=device.id,
                bytes_per_second=100.0,
                captured_at=now - timedelta(seconds=10),
            )
        )
        self.traffic_repository.add(
            TrafficSample(
                id=None,
                device_id=device.id,
                bytes_per_second=300.0,
                captured_at=now,
            )
        )

        rows = self.monitoring_service.get_device_table_rows()

        self.assertEqual(1, len(rows))
        self.assertEqual("Sensor", rows[0].name)
        self.assertEqual(300.0, rows[0].latest_speed_bps)
        self.assertEqual("Высокий", rows[0].risk_level)


if __name__ == "__main__":
    unittest.main()
