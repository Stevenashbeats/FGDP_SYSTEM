"""Resource & data paths — działa zarówno przy `python app.py` jak i w .app PyInstallera.

`bundle_dir()`     — read-only zasoby (SVG, default presety) — sys._MEIPASS w bundlu, parent skryptu w devie.
`user_data_dir()`  — writable katalog usera: ~/Library/Application Support/FGDP_SYSTEM (tworzony lazy).
"""

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "FGDP_SYSTEM"


def bundle_dir() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).parent


def user_data_dir() -> Path:
    base = Path.home() / "Library" / "Application Support" / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def seed_user_dir_from_bundle(subpath: str) -> Path:
    """Kopiuje katalog `subpath` z bundla do user_data_dir przy pierwszym uruchomieniu.
    Zwraca ścieżkę w user_data_dir."""
    target = user_data_dir() / subpath
    if target.exists():
        return target
    src = bundle_dir() / subpath
    if src.exists() and src.is_dir():
        shutil.copytree(src, target)
    else:
        target.mkdir(parents=True, exist_ok=True)
    return target


def seed_user_file_from_bundle(filename: str) -> Path:
    """Kopiuje plik z bundla do user_data_dir przy pierwszym uruchomieniu, jeśli nie istnieje.
    Zwraca docelową ścieżkę (może nie istnieć, jeśli źródła w bundlu też brak)."""
    target = user_data_dir() / filename
    if target.exists():
        return target
    src = bundle_dir() / filename
    if src.exists() and src.is_file():
        shutil.copy2(src, target)
    return target
