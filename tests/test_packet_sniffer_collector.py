"""Тесты сборщика трафика на основе сниффера пакетов."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from home_traffic_guard.collectors.packet_sniffer import PacketSnifferCollector
from home_traffic_guard.domain.models import Device


class PacketSnifferCollectorTestCase(unittest.TestCase):
    """Проверяет расчет B/s по окну наблюдений без реального захвата пакетов."""

    def test_collect_returns_zero_without_observations(self) -> None:
        """Если наблюдений нет, сборщик возвращает нулевую скорость."""
        collector = PacketSnifferCollector(window_seconds=5.0, auto_start=False)
        device = Device(id=1, name="Device", ip_address="192.168.1.20", mac_address=None)

        with patch("home_traffic_guard.collectors.packet_sniffer.time.monotonic", return_value=100.0):
            samples = collector.collect([device])

        self.assertEqual(1, len(samples))
        self.assertEqual(0.0, samples[0].bytes_per_second)

    def test_collect_uses_only_values_inside_window(self) -> None:
        """Значения вне окна наблюдений должны исключаться из расчета."""
        collector = PacketSnifferCollector(window_seconds=10.0, auto_start=False)
        device = Device(id=1, name="Device", ip_address="192.168.1.20", mac_address=None)

        collector.record_observation("192.168.1.20", 700, observed_at=89.0)  # Вне окна
        collector.record_observation("192.168.1.20", 500, observed_at=95.0)  # В окне
        collector.record_observation("192.168.1.20", 700, observed_at=99.0)  # В окне

        with patch("home_traffic_guard.collectors.packet_sniffer.time.monotonic", return_value=100.0):
            samples = collector.collect([device])

        self.assertEqual(1, len(samples))
        self.assertEqual(120.0, samples[0].bytes_per_second)


if __name__ == "__main__":
    unittest.main()
