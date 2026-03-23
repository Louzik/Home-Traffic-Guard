"""Тесты CLI-конфигурации запуска приложения."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from home_traffic_guard import main as main_module
from home_traffic_guard.config import AppConfig


class MainEntryPointTestCase(unittest.TestCase):
    """Проверяет разбор demo mode при запуске приложения."""

    def test_demo_mode_disabled_by_default(self) -> None:
        """Обычный запуск не должен включать demo mode."""
        config = AppConfig.default()
        with (
            patch.object(main_module, "HomeTrafficGuardApp") as app_cls,
            patch.object(main_module, "AppConfig") as config_cls,
            patch("sys.argv", ["home_traffic_guard"]),
            patch.dict(os.environ, {}, clear=False),
        ):
            config_cls.default.return_value = config
            app_cls.return_value.run.return_value = 0

            result = main_module.main()

        self.assertEqual(0, result)
        self.assertFalse(config.demo_mode)

    def test_demo_mode_enabled_by_flag(self) -> None:
        """Флаг --demo должен включать demo mode."""
        config = AppConfig.default()
        with (
            patch.object(main_module, "HomeTrafficGuardApp") as app_cls,
            patch.object(main_module, "AppConfig") as config_cls,
            patch("sys.argv", ["home_traffic_guard", "--demo"]),
            patch.dict(os.environ, {}, clear=False),
        ):
            config_cls.default.return_value = config
            app_cls.return_value.run.return_value = 0

            result = main_module.main()

        self.assertEqual(0, result)
        self.assertTrue(config.demo_mode)

    def test_demo_mode_enabled_by_env(self) -> None:
        """Переменная окружения должна включать demo mode."""
        config = AppConfig.default()
        with (
            patch.object(main_module, "HomeTrafficGuardApp") as app_cls,
            patch.object(main_module, "AppConfig") as config_cls,
            patch("sys.argv", ["home_traffic_guard"]),
            patch.dict(os.environ, {"HTG_DEMO_MODE": "1"}, clear=False),
        ):
            config_cls.default.return_value = config
            app_cls.return_value.run.return_value = 0

            result = main_module.main()

        self.assertEqual(0, result)
        self.assertTrue(config.demo_mode)


if __name__ == "__main__":
    unittest.main()
