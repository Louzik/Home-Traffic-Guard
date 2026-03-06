# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

project_root = Path.cwd()
entry_script = project_root / "src" / "home_traffic_guard" / "main.py"

block_cipher = None

# Явно собираем зависимости Qt/PySide6 для повышения совместимости на разных ПК.
pyside_datas = collect_data_files("PySide6")
pyside_binaries = collect_dynamic_libs("PySide6")
pyside_hiddenimports = collect_submodules("PySide6")

shiboken_binaries = collect_dynamic_libs("shiboken6")
shiboken_hiddenimports = collect_submodules("shiboken6")

a = Analysis(
    [str(entry_script)],
    pathex=[str(project_root / "src")],
    binaries=[*pyside_binaries, *shiboken_binaries],
    datas=[*pyside_datas],
    hiddenimports=[*pyside_hiddenimports, *shiboken_hiddenimports],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HomeTrafficGuard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="HomeTrafficGuard",
)
