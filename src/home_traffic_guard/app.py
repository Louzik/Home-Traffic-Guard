"""Корневой модуль сборки приложения."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from datetime import datetime, timedelta

from PySide6.QtWidgets import QApplication

from home_traffic_guard.analytics.baseline import BaselineAnalyzer
from home_traffic_guard.collectors.base import TrafficCollector
from home_traffic_guard.collectors.dummy_collector import DummyTrafficCollector
from home_traffic_guard.config import AppConfig
from home_traffic_guard.db.connection import Database
from home_traffic_guard.db.repositories import AlertRepository, DeviceRepository, TrafficSampleRepository
from home_traffic_guard.domain.models import Alert, Device
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

        if self._config.demo_mode:
            logger.info("Запуск в demo mode: добавляем тестовые устройства и оповещения")
            self._seed_devices(device_repository)
            self._seed_demo_alerts(device_repository, alert_repository)
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

    def _seed_demo_alerts(
        self,
        device_repository: DeviceRepository,
        alert_repository: AlertRepository,
    ) -> None:
        """Добавить демо-оповещения для проверки UI, если данных пока мало."""
        existing_alerts = alert_repository.list_recent(limit=500)
        if len(existing_alerts) >= 30:
            return
        existing_messages = {item.message for item in existing_alerts}

        devices = {item.name: item for item in device_repository.list_all() if item.id is not None}
        now = datetime.now()
        defaults = [
            ("WiFi Camera", "high", "Резкий всплеск трафика на потоке камеры", 6, False),
            ("WiFi Camera", "high", "Повторяющийся исходящий всплеск на неизвестный хост", 18, True),
            ("Smart TV", "medium", "Неожиданный рост трафика в режиме ожидания", 29, False),
            ("Smart TV", "low", "Обнаружена новая multicast-активность", 44, True),
            ("Voice Assistant", "medium", "Частота DNS-запросов выше baseline", 57, False),
            ("Voice Assistant", "low", "Фоновая синхронизация выше обычного уровня", 73, False),
            ("WiFi Camera", "high", "Длительный исходящий поток вне активных часов", 95, False),
            ("Smart TV", "medium", "Частые повторные API-запросы к медиа-узлу", 112, False),
            ("Voice Assistant", "low", "Периодическая синхронизация немного выше baseline", 131, True),
            ("WiFi Camera", "medium", "Необычный всплеск пакетов после простоя", 149, False),
            ("Smart TV", "low", "Зафиксирован кратковременный multicast-всплеск", 167, False),
            ("Voice Assistant", "high", "Крупная исходящая передача на новый адрес", 188, False),
            ("WiFi Camera", "low", "Небольшое отклонение трафика в режиме простоя", 205, True),
            ("Smart TV", "high", "Объем трафика превысил baseline-порог", 226, False),
            ("Voice Assistant", "medium", "Обнаружен продолжительный всплеск DNS-запросов", 244, False),
            ("Smart TV", "medium", "Множественные повторные подключения к облаку", 263, True),
            ("WiFi Camera", "high", "Серии резких всплесков трафика за последнюю минуту", 3, False),
            ("Smart TV", "medium", "Кратковременный рост фоновых подключений", 2, False),
            ("Voice Assistant", "low", "Незначительное отклонение после последней проверки", 1, False),
            ("WiFi Camera", "medium", "Повышенная частота коротких сессий", 5, False),
            ("Smart TV", "high", "Порог baseline превышен сразу после обновления", 4, False),
            ("Voice Assistant", "medium", "Всплеск DNS-запросов в текущем цикле", 2, False),
            ("WiFi Camera", "low", "Фоновая активность выше ожидаемой", 6, True),
            ("Smart TV", "low", "Обнаружен краткий всплеск служебного трафика", 7, False),
            ("Voice Assistant", "high", "Резкое увеличение исходящего трафика", 3, False),
            ("Smart TV", "medium", "Повторные обращения к облачному API", 5, True),
            (
                "WiFi Camera",
                "high",
                "Обнаружена длительная аномалия: устройство в течение нескольких циклов мониторинга "
                "отправляет большие объемы данных на ранее неиспользуемый внешний адрес, при этом "
                "частота соединений и суммарный трафик устойчиво превышают baseline и заданный порог.",
                2,
                False,
            ),
        ]

        for device_name, severity, message, minutes_ago, acknowledged in defaults:
            if message in existing_messages:
                continue
            device = devices.get(device_name)
            if device is None or device.id is None:
                continue

            created_at = now - timedelta(minutes=minutes_ago)
            acknowledged_at = created_at + timedelta(minutes=3) if acknowledged else None
            alert_repository.create(
                Alert(
                    id=None,
                    device_id=device.id,
                    message=message,
                    severity=severity,
                    created_at=created_at,
                    acknowledged=acknowledged,
                    acknowledged_at=acknowledged_at,
                )
            )
