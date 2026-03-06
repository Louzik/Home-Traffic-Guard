"""Сервис цикла мониторинга на базе таймера Qt."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QTimer

from home_traffic_guard.analytics.baseline import BaselineAnalyzer
from home_traffic_guard.collectors.base import TrafficCollector
from home_traffic_guard.db.repositories import AlertRepository, DeviceRepository, TrafficSampleRepository
from home_traffic_guard.domain.models import Alert, TrafficSample
from home_traffic_guard.notifications.service import NotificationService


@dataclass(slots=True)
class OverviewMetrics:
    """Метрики для отображения на странице обзора."""

    total_speed_bps: float
    active_devices: int
    alerts_last_24h: int
    last_sample_at: datetime | None


@dataclass(slots=True)
class DeviceTableRow:
    """Строка таблицы устройств для страницы `Устройства`."""

    device_id: int
    name: str
    ip_address: str
    mac_address: str | None
    latest_speed_bps: float
    risk_level: str
    updated_at: datetime | None
    created_at: datetime | None


@dataclass(slots=True)
class AlertTableRow:
    """Строка таблицы оповещений для страницы `Оповещения`."""

    alert_id: int
    device_name: str
    severity: str
    message: str
    created_at: datetime
    acknowledged: bool
    acknowledged_at: datetime | None


@dataclass(slots=True)
class AlertMetrics:
    """Метрики для карточек на странице `Оповещения`."""

    high_count: int
    medium_count: int
    low_count: int
    acknowledged_count: int


class MonitoringService(QObject):
    """Координирует периодический сбор, проверку baseline и создание оповещений."""

    def __init__(
        self,
        collector: TrafficCollector,
        device_repository: DeviceRepository,
        traffic_repository: TrafficSampleRepository,
        alert_repository: AlertRepository,
        analyzer: BaselineAnalyzer,
        notification_service: NotificationService,
        interval_ms: int,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._collector = collector
        self._device_repository = device_repository
        self._traffic_repository = traffic_repository
        self._alert_repository = alert_repository
        self._analyzer = analyzer
        self._notification_service = notification_service
        self._logger = logging.getLogger(self.__class__.__name__)

        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._on_tick)

    def start(self) -> None:
        """Запустить таймер мониторинга."""
        if self._timer.isActive():
            return
        self._start_collector_if_supported()
        self._timer.start()
        self._logger.info("Monitoring started")

    def stop(self) -> None:
        """Остановить таймер мониторинга."""
        if not self._timer.isActive():
            return
        self._timer.stop()
        self._stop_collector_if_supported()
        self._logger.info("Monitoring stopped")

    def get_interval_ms(self) -> int:
        """Вернуть текущий интервал мониторинга в миллисекундах."""
        return int(self._timer.interval())

    def set_interval_ms(self, interval_ms: int) -> None:
        """Изменить интервал мониторинга в миллисекундах."""
        if interval_ms <= 0:
            raise ValueError("interval_ms must be positive")

        self._timer.setInterval(interval_ms)
        self._set_collector_window_if_supported(interval_ms / 1000.0)
        self._logger.info("Monitoring interval updated to %s ms", interval_ms)

    def get_baseline_multiplier(self) -> float:
        """Вернуть текущий множитель baseline."""
        return float(self._analyzer.multiplier)

    def set_baseline_multiplier(self, multiplier: float) -> None:
        """Изменить множитель baseline."""
        self._analyzer.set_multiplier(multiplier)
        self._logger.info("Baseline multiplier updated to x%.2f", multiplier)

    def _on_tick(self) -> None:
        """Собрать измерения, сохранить их и создать оповещение при аномалии."""
        devices = self._device_repository.list_all()
        if not devices:
            self._logger.info("No devices found for monitoring")
            return

        collected = self._collector.collect(devices)
        for item in collected:
            recent_values = self._traffic_repository.list_recent_values(item.device_id)
            baseline = self._analyzer.calculate_baseline(recent_values)

            self._traffic_repository.add(
                TrafficSample(
                    id=None,
                    device_id=item.device_id,
                    bytes_per_second=item.bytes_per_second,
                    captured_at=item.captured_at,
                )
            )

            if self._analyzer.is_anomaly(item.bytes_per_second, baseline):
                threshold = baseline * self._analyzer.multiplier if baseline is not None else 0
                alert = self._alert_repository.create(
                    Alert(
                        id=None,
                        device_id=item.device_id,
                        message=(
                            f"Traffic spike detected: {item.bytes_per_second:.2f} B/s "
                            f"(baseline {baseline:.2f} B/s, threshold {threshold:.2f} B/s)"
                        ),
                        severity="high",
                        created_at=datetime.now(),
                    )
                )
                self._notification_service.notify_alert(alert)

    def get_overview_metrics(self) -> OverviewMetrics:
        """Собрать агрегированные метрики для страницы обзора."""
        devices = self._device_repository.list_all()
        now = datetime.now()
        active_cutoff = now - timedelta(minutes=1)

        total_speed_bps = 0.0
        active_devices = 0
        last_sample_at: datetime | None = None

        for device in devices:
            if device.id is None:
                continue

            latest_sample = self._traffic_repository.get_latest_sample(device.id)
            if latest_sample is None:
                continue

            total_speed_bps += latest_sample.bytes_per_second
            if latest_sample.captured_at >= active_cutoff:
                active_devices += 1
            if last_sample_at is None or latest_sample.captured_at > last_sample_at:
                last_sample_at = latest_sample.captured_at

        alerts_last_24h = self._alert_repository.count_since(now - timedelta(hours=24))
        return OverviewMetrics(
            total_speed_bps=total_speed_bps,
            active_devices=active_devices,
            alerts_last_24h=alerts_last_24h,
            last_sample_at=last_sample_at,
        )

    def get_device_table_rows(self) -> list[DeviceTableRow]:
        """Собрать строки таблицы устройств с актуальными метриками."""
        rows: list[DeviceTableRow] = []
        devices = self._device_repository.list_all()

        for device in devices:
            if device.id is None:
                continue

            latest_sample = self._traffic_repository.get_latest_sample(device.id)
            latest_speed_bps = latest_sample.bytes_per_second if latest_sample is not None else 0.0
            updated_at = latest_sample.captured_at if latest_sample is not None else None

            risk_level = "Нет данных"
            if latest_sample is not None:
                recent_values = self._traffic_repository.list_recent_values(device.id, limit=31)
                history_values = recent_values[1:] if len(recent_values) > 1 else []
                baseline = self._analyzer.calculate_baseline(history_values)
                risk_level = "Высокий" if self._analyzer.is_anomaly(latest_speed_bps, baseline) else "Низкий"

            rows.append(
                DeviceTableRow(
                    device_id=device.id,
                    name=device.name,
                    ip_address=device.ip_address,
                    mac_address=device.mac_address,
                    latest_speed_bps=latest_speed_bps,
                    risk_level=risk_level,
                    updated_at=updated_at,
                    created_at=device.created_at,
                )
            )

        return rows

    def get_alert_metrics(self) -> AlertMetrics:
        """Собрать метрики по оповещениям за последние 24 часа."""
        recent_alerts = self._alert_repository.list_recent(limit=1000)
        cutoff = datetime.now() - timedelta(hours=24)

        high_count = 0
        medium_count = 0
        low_count = 0
        acknowledged_count = 0

        for alert in recent_alerts:
            if alert.created_at < cutoff:
                continue

            severity = alert.severity.lower()
            if severity == "high":
                high_count += 1
            elif severity == "medium":
                medium_count += 1
            else:
                low_count += 1

            if alert.acknowledged:
                acknowledged_count += 1

        return AlertMetrics(
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            acknowledged_count=acknowledged_count,
        )

    def get_alert_table_rows(
        self,
        severity_filter: str | None = None,
        only_unacknowledged: bool = False,
        limit: int = 300,
    ) -> list[AlertTableRow]:
        """Собрать строки таблицы оповещений с фильтрацией."""
        alerts = self._alert_repository.list_recent(limit=limit)
        devices = self._device_repository.list_all()
        device_names = {device.id: device.name for device in devices if device.id is not None}

        rows: list[AlertTableRow] = []
        severity_filter_normalized = severity_filter.lower() if severity_filter else None

        for alert in alerts:
            alert_severity = alert.severity.lower()
            if severity_filter_normalized and alert_severity != severity_filter_normalized:
                continue
            if only_unacknowledged and alert.acknowledged:
                continue

            rows.append(
                AlertTableRow(
                    alert_id=int(alert.id or 0),
                    device_name=device_names.get(alert.device_id, f"ID {alert.device_id}"),
                    severity=alert.severity,
                    message=alert.message,
                    created_at=alert.created_at,
                    acknowledged=alert.acknowledged,
                    acknowledged_at=alert.acknowledged_at,
                )
            )

        return rows

    def set_alert_acknowledged(self, alert_id: int, acknowledged: bool) -> None:
        """Изменить статус подтверждения оповещения."""
        if alert_id <= 0:
            return
        self._alert_repository.set_acknowledged(
            alert_id=alert_id,
            acknowledged=acknowledged,
            changed_at=datetime.now(),
        )

    def _start_collector_if_supported(self) -> None:
        """Запустить коллектор, если он поддерживает жизненный цикл start/stop."""
        start_method = getattr(self._collector, "start", None)
        if callable(start_method):
            start_method()

    def _stop_collector_if_supported(self) -> None:
        """Остановить коллектор, если он поддерживает жизненный цикл start/stop."""
        stop_method = getattr(self._collector, "stop", None)
        if callable(stop_method):
            stop_method()

    def _set_collector_window_if_supported(self, window_seconds: float) -> None:
        """Обновить окно сбора у коллектора, если он это поддерживает."""
        update_method = getattr(self._collector, "set_window_seconds", None)
        if callable(update_method):
            update_method(window_seconds)
