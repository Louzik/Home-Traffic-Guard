"""Алгоритмы обнаружения аномалий на основе baseline."""

from __future__ import annotations

from statistics import fmean
from typing import Iterable


class BaselineAnalyzer:
    """Обнаруживает аномалии, сравнивая текущее значение со средним историческим."""

    def __init__(self, multiplier: float = 2.0) -> None:
        if multiplier <= 1.0:
            raise ValueError("multiplier must be greater than 1.0")
        self._multiplier = multiplier

    @property
    def multiplier(self) -> float:
        """Вернуть множитель порога аномалии."""
        return self._multiplier

    def set_multiplier(self, multiplier: float) -> None:
        """Изменить множитель порога аномалии."""
        if multiplier <= 1.0:
            raise ValueError("multiplier must be greater than 1.0")
        self._multiplier = multiplier

    def calculate_baseline(self, values: Iterable[float]) -> float | None:
        """Вычислить средний baseline по переданным историческим значениям."""
        numeric_values = list(values)
        if not numeric_values:
            return None
        return float(fmean(numeric_values))

    def is_anomaly(self, current_value: float, baseline: float | None) -> bool:
        """Вернуть `True`, если текущее значение выше порога baseline * multiplier."""
        if baseline is None or baseline <= 0:
            return False
        return current_value > baseline * self._multiplier
