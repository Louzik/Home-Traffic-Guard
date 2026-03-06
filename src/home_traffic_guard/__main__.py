"""Точка входа пакета для запуска Home Traffic Guard как модуля."""

try:
    # Нормальный путь при запуске как модуля: python -m home_traffic_guard
    from .main import main
except ImportError:
    # Защитный путь, если файл выполняется как скрипт без package-контекста.
    from home_traffic_guard.main import main

raise SystemExit(main())
