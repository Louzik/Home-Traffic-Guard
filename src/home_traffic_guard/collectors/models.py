"""Модели данных для слоя сбора."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class CollectedTraffic:
    """Одно измерение трафика, полученное модулем сбора."""

    device_id: int
    bytes_per_second: float
    captured_at: datetime
