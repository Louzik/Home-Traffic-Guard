"""Тесты алгоритма обнаружения аномалий baseline."""

from __future__ import annotations

import unittest

from home_traffic_guard.analytics.baseline import BaselineAnalyzer


class BaselineAnalyzerTestCase(unittest.TestCase):
    """Проверяет расчет baseline и поведение порога аномалий."""

    def test_calculate_baseline_average(self) -> None:
        """Среднее должно считаться по всем историческим значениям."""
        analyzer = BaselineAnalyzer(multiplier=2.0)

        baseline = analyzer.calculate_baseline([100.0, 200.0, 300.0])

        self.assertEqual(200.0, baseline)

    def test_is_anomaly_when_value_exceeds_double_baseline(self) -> None:
        """Значение выше baseline * multiplier должно считаться аномалией."""
        analyzer = BaselineAnalyzer(multiplier=2.0)

        result = analyzer.is_anomaly(current_value=250.0, baseline=120.0)

        self.assertTrue(result)

    def test_is_not_anomaly_when_value_equals_threshold(self) -> None:
        """Сравнение с порогом строгое: только оператор `>`."""
        analyzer = BaselineAnalyzer(multiplier=2.0)

        result = analyzer.is_anomaly(current_value=240.0, baseline=120.0)

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
