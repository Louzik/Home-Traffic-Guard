"""Корневой модуль сборки приложения."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable

from PySide6.QtWidgets import QApplication

from home_traffic_guard.analytics.baseline import BaselineAnalyzer
from home_traffic_guard.collectors.base import TrafficCollector
from home_traffic_guard.collectors.dummy_collector import DummyTrafficCollector
from home_traffic_guard.config import AppConfig
from home_traffic_guard.db.connection import Database
from home_traffic_guard.db.repositories import AlertRepository, DeviceRepository, TrafficSampleRepository
from home_traffic_guard.domain.models import Device
from home_traffic_guard.logging_setup import setup_logging
from home_traffic_guard.notifications.service import NotificationService
from home_traffic_guard.services.monitoring_service import MonitoringService
from home_traffic_guard.ui.main_window import MainWindow


class HomeTrafficGuardApp:
    """Собирает и запускает настольное приложение Home Traffic Guard."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def run(self) -> int:
        """Инициализировать зависимости и запустить цикл событий Qt."""
        setup_logging(self._config.log_path)
        logger = logging.getLogger(self.__class__.__name__)
        logger.info("Starting Home Traffic Guard")

        database = Database(self._config.db_path)
        database.initialize()

        device_repository = DeviceRepository(database.connect)
        traffic_repository = TrafficSampleRepository(database.connect)
        alert_repository = AlertRepository(database.connect)

        self._seed_devices(device_repository)
        collector = self._build_collector()

        monitoring_service = MonitoringService(
            collector=collector,
            device_repository=device_repository,
            traffic_repository=traffic_repository,
            alert_repository=alert_repository,
            analyzer=BaselineAnalyzer(multiplier=self._config.baseline_multiplier),
            notification_service=NotificationService(),
            interval_ms=self._config.monitoring_interval_ms,
        )

        qt_app = QApplication.instance() or QApplication(sys.argv)
        window = MainWindow(monitoring_service=monitoring_service)
        window.show()

        return qt_app.exec()

    def _build_collector(self) -> TrafficCollector:
        """Создать реальный коллектор трафика и откатиться на dummy при ошибке."""
        logger = logging.getLogger(self.__class__.__name__)

        try:
            packet_sniffer_factory = self._load_packet_sniffer_factory()
            collector = packet_sniffer_factory(
                window_seconds=max(self._config.monitoring_interval_ms / 1000.0, 1.0),
                auto_start=True,
            )
            # Проверяем, что сборщик действительно может стартовать в текущем окружении.
            collector.start()
            collector.stop()
            logger.info("Используется реальный сбор трафика через PacketSnifferCollector")
            return collector
        except RuntimeError as error:
            logger.warning(
                "Реальный сбор трафика недоступен (%s). Используем DummyTrafficCollector",
                error,
            )
            return DummyTrafficCollector()
        except Exception:
            logger.exception("Ошибка инициализации PacketSnifferCollector, используем DummyTrafficCollector")
            return DummyTrafficCollector()

    @staticmethod
    def _load_packet_sniffer_factory() -> Callable[..., TrafficCollector]:
        """Лениво импортировать PacketSnifferCollector, чтобы сбой scapy не ломал запуск приложения."""
        from home_traffic_guard.collectors.packet_sniffer import PacketSnifferCollector

        return PacketSnifferCollector

    def _seed_devices(self, device_repository: DeviceRepository) -> None:
        """Добавить устройства по умолчанию при первом запуске, если таблица пуста."""
        if device_repository.list_all():
            return

        defaults = [
            Device(id=None, name="WiFi Camera", ip_address="192.168.1.20", mac_address="AA:BB:CC:DD:EE:01"),
            Device(id=None, name="Smart TV", ip_address="192.168.1.21", mac_address="AA:BB:CC:DD:EE:02"),
            Device(id=None, name="Voice Assistant", ip_address="192.168.1.22", mac_address="AA:BB:CC:DD:EE:03"),
        ]

        for item in defaults:
            device_repository.create(item)
