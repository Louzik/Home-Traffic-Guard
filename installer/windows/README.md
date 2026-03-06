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
