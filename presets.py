"""System presetów: zapis/odczyt mapping + output bank jako nazwany preset."""

import json
from dataclasses import asdict
from pathlib import Path

from mappings import MappingStore
from output_map import OutputBank, OutputCell
from paths import seed_user_dir_from_bundle

PRESETS_DIR = seed_user_dir_from_bundle("presets")


def list_presets() -> list[dict]:
    """Zwraca listę {'file': Path, 'name': str} posortowaną po nazwie pliku."""
    if not PRESETS_DIR.exists():
        return []
    presets = []
    for p in sorted(PRESETS_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text())
            name = data.get("name", p.stem)
        except Exception:
            name = p.stem
        presets.append({"file": p, "name": name})
    return presets


def save_preset(name: str, mapping: MappingStore, bank: OutputBank) -> Path:
    """Zapisuje aktualny stan jako preset. Zwraca ścieżkę pliku."""
    PRESETS_DIR.mkdir(exist_ok=True)
    existing = list_presets()
    idx = len(existing) + 1
    filename = f"preset_{idx:02d}.json"
    path = PRESETS_DIR / filename

    data = {
        "name": name,
        "mapping": mapping.all(),
        "outputs": {oid: asdict(c) for oid, c in bank.items()},
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True))
    return path


def load_preset(path: Path, mapping: MappingStore, bank: OutputBank) -> str:
    """Ładuje preset z pliku do mapping i bank. Zwraca nazwę presetu."""
    data = json.loads(path.read_text())

    # mapping
    mapping.clear()
    for pad_id, m in data.get("mapping", {}).items():
        if isinstance(m, dict) and "channel" in m and "note" in m:
            mapping.learn(pad_id, int(m["channel"]), int(m["note"]))

    # outputs
    bank.reset_to_defaults()
    for oid, d in data.get("outputs", {}).items():
        cell = bank.get(oid)
        if cell is None or not isinstance(d, dict):
            continue
        for k, v in d.items():
            if hasattr(cell, k):
                setattr(cell, k, v)

    return data.get("name", path.stem)
