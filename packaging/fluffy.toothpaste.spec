# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 6.15+ supports Python 3.14 (see PyInstaller changelog).
# Build from repo root: uv run pyinstaller packaging/fluffy.toothpaste.spec

from pathlib import Path

block_cipher = None

project_root = Path(SPEC).resolve().parent.parent

a = Analysis(
    [str(project_root / "src" / "main.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[(str(project_root / "fluffy-toothpaste.png"), ".")],
    hiddenimports=["PIL._tkinter_finder"],
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
    name="fluffy-toothpaste",
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
    name="fluffy-toothpaste",
)
