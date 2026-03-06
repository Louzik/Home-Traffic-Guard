"""Защитная точка входа для Windows-сборки с записью crash-лога."""

from __future__ import annotations

import os
import traceback
from datetime import datetime
from pathlib import Path


def _app_state_dir() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        base_dir = Path(local_app_data)
        return base_dir / "HomeTrafficGuard"
    return Path.home() / ".home_traffic_guard"


def _write_crash_log(trace: str) -> Path:
    state_dir = _app_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    log_path = state_dir / "startup_crash.log"
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_path.open("a", encoding="utf-8") as file:
        file.write(f"[{stamp}] Startup failure\n")
        file.write(trace)
        file.write("\n")
    return log_path


def _show_fatal_message(message: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, "Home Traffic Guard", 0x10)
    except Exception:
        # Если API недоступен, просто оставляем запись в лог.
        return


def main() -> int:
    """Запустить приложение и при ошибке сохранить диагностический лог."""
    try:
        from home_traffic_guard.main import main as app_main

        return int(app_main())
    except Exception:
        trace = traceback.format_exc()
        crash_log = _write_crash_log(trace)
        _show_fatal_message(
            "Home Traffic Guard не удалось запустить.\n\n"
            f"Детали ошибки сохранены в:\n{crash_log}"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
