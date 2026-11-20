# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build specification for AegisKey Windows distributions (onedir & portable)."""

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT_DIR = Path(SPECPATH).resolve().parents[1]
ENTRY_SCRIPT = ROOT_DIR / "src" / "password_generator" / "__main__.py"

build_mode = os.environ.get("AEGISKEY_BUILD_MODE", "onedir").strip().lower()
app_name = os.environ.get("AEGISKEY_APP_NAME", "AegisKey").strip() or "AegisKey"
icon_env = os.environ.get("AEGISKEY_ICON_PATH", "").strip()
icon_path = Path(icon_env) if icon_env else ROOT_DIR / "build" / "windows" / "assets" / "AegisKey.ico"
version_file_env = os.environ.get("AEGISKEY_VERSION_FILE", "").strip()
version_file = Path(version_file_env) if version_file_env else None

datas = collect_data_files("password_generator")

a = Analysis(
    [str(ENTRY_SCRIPT)],
    pathex=[str(ROOT_DIR / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "ruff", "pyrefly"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

common_exe_kwargs = {
    "name": app_name,
    "debug": False,
    "bootloader_ignore_signals": False,
    "strip": False,
    "upx": False,
    "console": False,
    "disable_windowed_traceback": False,
    "argv_emulation": False,
    "target_arch": "x86_64",
    "icon": str(icon_path) if icon_path.exists() else None,
    "version": str(version_file) if version_file and version_file.exists() else None,
}

if build_mode == "onefile":
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        runtime_tmpdir=None,
        **common_exe_kwargs,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        **common_exe_kwargs,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=app_name,
    )
