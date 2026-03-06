# Установщик для Windows

В этой папке лежат файлы для сборки:

- `HomeTrafficGuard.spec` — конфигурация PyInstaller.
- `HomeTrafficGuard.iss` — скрипт Inno Setup для создания `setup.exe`.
- `build_installer.bat` — полный цикл сборки (PyInstaller + Inno Setup).
- `build_installer.ps1` — аналогичный цикл сборки через PowerShell.

## Требования на Windows

1. Python 3.11+ (`py -3.11` или `python` в `PATH`).
2. Установленный Inno Setup 6 (компилятор `ISCC.exe`).
3. Интернет для установки build-зависимостей (`pyinstaller` и пакет проекта).
4. Интернет во время сборки для загрузки `Microsoft Visual C++ Redistributable (x64)`.

## Что входит в setup.exe

Установщик включает и автоматически устанавливает `Microsoft Visual C++ Redistributable 2015-2022 (x64)`.
Поэтому запуск `setup.exe` требует права администратора.

## Если приложение не стартует у тестировщика

Попросите прислать файл:

```text
%LOCALAPPDATA%\HomeTrafficGuard\startup_crash.log
```

Этот лог создается защитным launcher-скриптом при ошибке запуска.

## Быстрый запуск

Откройте `cmd` в корне проекта (`home-traffic-guard`) и выполните:

```bat
installer\windows\build_installer.bat
```

Итоговый установщик появится в:

```text
installer\windows\output\HomeTrafficGuardSetup.exe
```

## Если нужен только portable build

Используйте только PyInstaller:

```bat
python -m PyInstaller installer\windows\HomeTrafficGuard.spec --noconfirm --clean
```

Готовая папка приложения будет в `dist\HomeTrafficGuard`.
