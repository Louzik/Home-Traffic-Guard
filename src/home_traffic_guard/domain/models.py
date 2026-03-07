"""Базовые доменные модели, используемые во всем приложении."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Device:
    """Устройство умного дома, генерирующее сетевой трафик."""

    id: int | None
    name: str
    ip_address: str
    mac_address: str | None
    created_at: datetime | None = None


@dataclass(slots=True)
class TrafficSample:
    """Измерение трафика устройства в конкретный момент времени."""

    id: int | None
    device_id: int
    bytes_per_second: float
    captured_at: datetime


@dataclass(slots=True)
class Alert:
    """Оповещение об аномалии, созданное аналитическими правилами."""

    id: int | None
    device_id: int
    message: str
    severity: str
    created_at: datetime
    acknowledged: bool = False
    acknowledged_at: datetime | None = None
