"""Простой детерминированный сборщик для MVP и тестов."""

from __future__ import annotations

from datetime import datetime

from home_traffic_guard.collectors.models import CollectedTraffic
from home_traffic_guard.domain.models import Device


class DummyTrafficCollector:
    """Генерирует синтетические значения трафика без внешних зависимостей."""

    def __init__(self) -> None:
        self._tick = 0

    def collect(self, devices: list[Device]) -> list[CollectedTraffic]:
        """Сгенерировать по одному синтетическому измерению на устройство за цикл."""
        self._tick += 1
        samples: list[CollectedTraffic] = []
        now = datetime.now()

        for index, device in enumerate(devices, start=1):
            if device.id is None:
                continue
            base = 120.0 + (index * 30)
            spike = 450.0 if self._tick % 8 == 0 else 0.0
            value = base + (self._tick % 5) * 20 + spike
            samples.append(
                CollectedTraffic(
                    device_id=device.id,
                    bytes_per_second=value,
                    captured_at=now,
                )
            )
        return samples
