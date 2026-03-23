# Home Traffic Guard

MVP desktop application for monitoring smart home traffic.

## Run

```bash
python -m home_traffic_guard
```

If the package is not installed yet:

```bash
PYTHONPATH=src python -m home_traffic_guard
```

## Demo mode

По умолчанию приложение больше не добавляет тестовые устройства и оповещения в базу.

Для локальной проверки UI используйте demo mode:

```bash
PYTHONPATH=src python -m home_traffic_guard --demo
```

или через переменную окружения:

```bash
HTG_DEMO_MODE=1 PYTHONPATH=src python -m home_traffic_guard
```

## Реальный сбор трафика

Приложение использует захват пакетов (`scapy`) для реального сбора трафика по устройствам.
Если захват пакетов недоступен в текущем окружении, приложение автоматически переключится на `DummyTrafficCollector`.
На некоторых системах для захвата пакетов могут потребоваться повышенные права.

## Интервал обновления

По умолчанию мониторинг выполняется раз в 15 секунд.
Изменить интервал можно в разделе `Настройки` приложения.
Поддерживаются интервалы: 5/15/30 секунд, 1/3/5/10/15/30 минут, 1/2/3/12 часов, раз в сутки.
Выбранное значение сохраняется между запусками.

## Test

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

## Windows installer

Файлы сборки установщика Windows находятся в:

```text
installer/windows
```

Подробная инструкция:

```text
installer/windows/README.md
```

Для автосборки в GitHub Actions добавлен workflow:

```text
.github/workflows/windows-installer.yml
```

После выполнения workflow готовый `HomeTrafficGuardSetup.exe` доступен в артефактах run.

Текущий setup.exe также включает автоматическую установку `Microsoft Visual C++ Redistributable 2015-2022 (x64)`.

Если приложение не запускается на Windows, диагностический лог старта ищите в:

```text
%LOCALAPPDATA%\HomeTrafficGuard\startup_crash.log
```
