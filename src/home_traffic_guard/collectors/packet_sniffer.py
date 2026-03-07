"""Сборщик реального трафика на основе захвата пакетов."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from datetime import datetime
from threading import Lock
from typing import Any, Sequence

from home_traffic_guard.collectors.models import CollectedTraffic
from home_traffic_guard.domain.models import Device

try:
    from scapy.all import AsyncSniffer  # type: ignore[import-not-found]
    from scapy.layers.inet import IP  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - зависит от окружения выполнения
    AsyncSniffer = None
    IP = None


class PacketSnifferCollector:
    """Собирает трафик устройств по их IP-адресам через сетевой сниффер."""

    def __init__(
        self,
        window_seconds: float = 5.0,
        interfaces: Sequence[str] | None = None,
        auto_start: bool = True,
    ) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        self._window_seconds = window_seconds
        self._interfaces = list(interfaces) if interfaces else None
        self._auto_start = auto_start
        self._logger = logging.getLogger(self.__class__.__name__)

        self._sniffer: Any | None = None
        self._started = False
        self._lock = Lock()
        self._ip_samples: dict[str, deque[tuple[float, int]]] = defaultdict(deque)

    def start(self) -> None:
        """Запустить фоновый захват пакетов."""
        if self._started:
            return
        if AsyncSniffer is None or IP is None:
            raise RuntimeError("Для реального сбора трафика требуется пакет scapy.")

        self._sniffer = AsyncSniffer(
            prn=self._on_packet,
            store=False,
            iface=self._interfaces,
        )
        self._sniffer.start()
        self._started = True
        self._logger.info("Запущен захват сетевых пакетов")

    def stop(self) -> None:
        """Остановить фоновый захват пакетов."""
        if not self._started:
            return

        try:
            if self._sniffer is not None:
                self._sniffer.stop()
        except Exception as error:
            message = str(error).lower()
            if "permission denied" in message or "/dev/bpf" in message:
                raise RuntimeError(
                    "Недостаточно прав для захвата пакетов (доступ к /dev/bpf)."
                ) from None
            raise RuntimeError("Ошибка остановки захвата пакетов.") from error
        finally:
            self._started = False
            self._sniffer = None
            self._logger.info("Захват сетевых пакетов остановлен")

    def collect(self, devices: list[Device]) -> list[CollectedTraffic]:
        """Вернуть текущую скорость трафика (B/s) для каждого устройства."""
        if self._auto_start and not self._started:
            self.start()

        captured_at = datetime.now()
        now_monotonic = time.monotonic()
        samples: list[CollectedTraffic] = []

        with self._lock:
            self._prune_locked(now_monotonic)
            for device in devices:
                if device.id is None:
                    continue
                total_bytes = self._sum_device_bytes_locked(device.ip_address)
                samples.append(
                    CollectedTraffic(
                        device_id=device.id,
                        bytes_per_second=total_bytes / self._window_seconds,
                        captured_at=captured_at,
                    )
                )

        return samples

    def set_window_seconds(self, window_seconds: float) -> None:
        """Обновить размер окна расчета скорости в секундах."""
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        with self._lock:
            self._window_seconds = window_seconds
            self._prune_locked(time.monotonic())

    def record_observation(
        self,
        ip_address: str,
        bytes_count: int,
        observed_at: float | None = None,
    ) -> None:
        """Добавить наблюдение трафика для IP-адреса (используется и в тестах)."""
        if not ip_address or bytes_count <= 0:
            return

        moment = observed_at if observed_at is not None else time.monotonic()
        with self._lock:
            self._ip_samples[ip_address].append((moment, bytes_count))

    def _on_packet(self, packet: Any) -> None:
        """Обработать пакет и сохранить его размер по source/destination IP."""
        if IP is None:
            return
        if not packet.haslayer(IP):
            return

        ip_layer = packet[IP]
        packet_size = int(len(packet))
        observed_at = time.monotonic()

        self.record_observation(str(ip_layer.src), packet_size, observed_at)
        self.record_observation(str(ip_layer.dst), packet_size, observed_at)

    def _sum_device_bytes_locked(self, ip_address: str) -> float:
        values = self._ip_samples.get(ip_address)
        if not values:
            return 0.0
        return float(sum(item[1] for item in values))

    def _prune_locked(self, now_monotonic: float) -> None:
        cutoff = now_monotonic - self._window_seconds
        empty_ips: list[str] = []

        for ip_address, values in self._ip_samples.items():
            while values and values[0][0] < cutoff:
                values.popleft()
            if not values:
                empty_ips.append(ip_address)

        for ip_address in empty_ips:
            self._ip_samples.pop(ip_address, None)
