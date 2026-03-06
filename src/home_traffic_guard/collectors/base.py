"""Интерфейсы модулей сбора."""

from __future__ import annotations

from typing import Protocol

from home_traffic_guard.collectors.models import CollectedTraffic
from home_traffic_guard.domain.models import Device


class TrafficCollector(Protocol):
    """Протокол для компонентов, собирающих трафик по устройствам."""

    def collect(self, devices: list[Device]) -> list[CollectedTraffic]:
        """Собрать измерения трафика для переданных устройств."""
        ...
