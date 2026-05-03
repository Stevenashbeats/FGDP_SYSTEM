# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — buduje FGDP_SYSTEM.app (Apple Silicon, ad-hoc signed).

Build:
    pyinstaller --noconfirm FGDP_SYSTEM.spec

Output:
    dist/FGDP_SYSTEM.app
"""

import os

from PyInstaller.utils.hooks import collect_submodules

datas = [
    ("PADS DESIGN_01.svg", "."),
    ("PADS DESIGN.svg", "."),
    ("PAD DESIGN.svg", "."),
    ("presets", "presets"),       # seeded do user_data_dir przy pierwszym uruchomieniu
]
# mappings.json jest gitignored — bundlujemy tylko jeśli istnieje (lokalna kopia usera).
# Brak pliku w bundlu = defaults z DEFAULT_MAPPING przy pierwszym starcie.
if os.path.exists("mappings.json"):
    datas.append(("mappings.json", "."))

hiddenimports = [
    "rtmidi",
    "mido.backends.rtmidi",
] + collect_submodules("mido.backends")

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FGDP_SYSTEM",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch="arm64",
    codesign_identity="-",        # ad-hoc sign (darmowy)
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="FGDP_SYSTEM",
)

app = BUNDLE(
    coll,
    name="FGDP_SYSTEM.app",
    icon="icon.icns",
    bundle_identifier="com.kacpernowak.fgdp_system",
    info_plist={
        "CFBundleName": "FGDP_SYSTEM",
        "CFBundleDisplayName": "FGDP_SYSTEM",
        "CFBundleShortVersionString": "0.2",
        "CFBundleVersion": "0.2",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
    },
)
