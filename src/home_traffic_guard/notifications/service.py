"""Сервис доставки уведомлений."""

from __future__ import annotations

import logging

from home_traffic_guard.domain.models import Alert


class NotificationService:
    """Обрабатывает уведомления об оповещениях мониторинга."""

    def __init__(self) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)

    def notify_alert(self, alert: Alert) -> None:
        """Отправить уведомление об оповещении через канал логирования."""
        self._logger.warning(
            "ALERT: device_id=%s severity=%s message=%s",
            alert.device_id,
            alert.severity,
            alert.message,
        )
