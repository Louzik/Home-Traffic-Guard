@echo off
setlocal

REM Скрипт сборки Windows-установщика:
REM 1) собирает приложение через PyInstaller
REM 2) упаковывает setup.exe через Inno Setup

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..") do set "PROJECT_ROOT=%%~fI"

cd /d "%PROJECT_ROOT%" || (
    echo [ERROR] Не удалось перейти в корень проекта.
    exit /b 1
)

set "BUILD_VENV=.venv-build-win"
set "PYTHON_EXE=%PROJECT_ROOT%\%BUILD_VENV%\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [INFO] Создаем окружение сборки %BUILD_VENV%...
    py -3.11 -m venv "%BUILD_VENV%" 2>nul
    if errorlevel 1 (
        python -m venv "%BUILD_VENV%"
        if errorlevel 1 (
            echo [ERROR] Не удалось создать виртуальное окружение.
            exit /b 1
        )
    )
)

echo [INFO] Устанавливаем зависимости сборки...
"%PYTHON_EXE%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [ERROR] Ошибка обновления pip/setuptools/wheel.
    exit /b 1
)

"%PYTHON_EXE%" -m pip install -e . pyinstaller
if errorlevel 1 (
    echo [ERROR] Ошибка установки зависимостей проекта или pyinstaller.
    exit /b 1
)

echo [INFO] Собираем приложение через PyInstaller...
"%PYTHON_EXE%" -m PyInstaller installer\windows\HomeTrafficGuard.spec --noconfirm --clean
if errorlevel 1 (
    echo [ERROR] Ошибка сборки PyInstaller.
    exit /b 1
)

set "PREREQS_DIR=installer\windows\prereqs"
set "VCREDIST_PATH=%PREREQS_DIR%\vc_redist.x64.exe"
set "VCREDIST_URL=https://aka.ms/vs/17/release/vc_redist.x64.exe"

if not exist "%PREREQS_DIR%" (
    mkdir "%PREREQS_DIR%"
)

echo [INFO] Загружаем Microsoft Visual C++ Redistributable (x64)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '%VCREDIST_URL%' -OutFile '%PROJECT_ROOT%\%VCREDIST_PATH%'"
if errorlevel 1 (
    echo [ERROR] Не удалось скачать vc_redist.x64.exe.
    exit /b 1
)

if not exist "%VCREDIST_PATH%" (
    echo [ERROR] Файл vc_redist.x64.exe не найден после загрузки.
    exit /b 1
)

set "ISCC_EXE="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%ChocolateyInstall%\bin\ISCC.exe" set "ISCC_EXE=%ChocolateyInstall%\bin\ISCC.exe"

if not defined ISCC_EXE (
    echo [ERROR] Не найден ISCC.exe (Inno Setup 6).
    echo [INFO] Установите Inno Setup и повторите команду.
    exit /b 1
)

echo [INFO] Собираем setup.exe через Inno Setup...
"%ISCC_EXE%" "installer\windows\HomeTrafficGuard.iss"
if errorlevel 1 (
    echo [ERROR] Ошибка сборки Inno Setup.
    exit /b 1
)

echo.
echo [OK] Готово.
echo [OK] Установщик: installer\windows\output\HomeTrafficGuardSetup.exe

endlocal
exit /b 0
