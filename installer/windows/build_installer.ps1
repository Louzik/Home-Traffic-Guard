$ErrorActionPreference = "Stop"

# Скрипт сборки Windows-установщика:
# 1) PyInstaller -> dist\HomeTrafficGuard
# 2) Inno Setup -> installer\windows\output\HomeTrafficGuardSetup.exe

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
Set-Location $ProjectRoot

function Invoke-External {
    param (
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $false)]
        [string[]]$Arguments = @()
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Команда завершилась с кодом ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

$BuildVenv = ".venv-build-win"
$PythonExe = Join-Path $ProjectRoot "$BuildVenv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "[INFO] Создаем окружение сборки $BuildVenv..."
    try {
        py -3.11 -m venv $BuildVenv
    } catch {
        python -m venv $BuildVenv
    }
}

Write-Host "[INFO] Устанавливаем зависимости сборки..."
Invoke-External -FilePath $PythonExe -Arguments @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")
Invoke-External -FilePath $PythonExe -Arguments @("-m", "pip", "install", "-e", ".", "pyinstaller")

Write-Host "[INFO] Собираем приложение через PyInstaller..."
Invoke-External -FilePath $PythonExe -Arguments @(
    "-m",
    "PyInstaller",
    "installer\windows\HomeTrafficGuard.spec",
    "--noconfirm",
    "--clean"
)

$IsccCandidates = @(
    "${env:ChocolateyInstall}\bin\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
)

$IsccExe = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $IsccExe) {
    $IsccCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($IsccCommand) {
        $IsccExe = $IsccCommand.Source
    }
}

if (-not $IsccExe) {
    throw "Не найден ISCC.exe (Inno Setup 6). Установите Inno Setup и повторите команду."
}

Write-Host "[INFO] Собираем setup.exe через Inno Setup..."
Invoke-External -FilePath $IsccExe -Arguments @("installer\windows\HomeTrafficGuard.iss")

Write-Host ""
Write-Host "[OK] Готово."
$InstallerPath = Join-Path $ProjectRoot "installer\windows\output\HomeTrafficGuardSetup.exe"
if (-not (Test-Path $InstallerPath)) {
    throw "Установщик не найден: $InstallerPath"
}
Write-Host "[OK] Установщик: installer\windows\output\HomeTrafficGuardSetup.exe"
