"""Mapowanie pad/key id <-> (channel, note) dla Yamaha FGDP-50.

DEFAULT_MAPPING to nasza wzorcowa baza — pochodzi z User Trigger zaprogramowanego
na sprzęcie:
  - 18 czarnych padów  -> kanał 16 (0-indexed: 15), noty 36..53
  - 8  klawiszy RGB    -> kanał 15 (0-indexed: 14), noty 54..61

Wszystkie kolejne iteracje sampler/UI/audio bazują na tym mapowaniu.

mappings.json (jeśli istnieje obok pliku) nadpisuje wybrane wpisy — pozwala na
lokalne korekty bez ruszania kodu. Brak pliku = czyste defaulty.
"""

import json
from pathlib import Path

from paths import seed_user_file_from_bundle

DEFAULT_VELOCITY = 100
STORE_PATH = seed_user_file_from_bundle("mappings.json")

ALL_IDS: tuple[str, ...] = tuple(
    [f"pad-{i:02d}" for i in range(1, 19)] + [f"key-{i:02d}" for i in range(1, 9)]
)

# Kanały MIDI w 0-indexed (do bezpośredniego użycia z mido.Message).
# Czyli 14 = kanał 15 na sprzęcie, 15 = kanał 16 na sprzęcie.
PAD_CHANNEL = 15
KEY_CHANNEL = 14

# Wzorcowy mapping dla FGDP-50 (User Trigger).
DEFAULT_MAPPING: dict[str, dict[str, int]] = {
    # --- 18 czarnych padów (kanał 16 / 0-idx 15) ---
    "pad-01": {"channel": PAD_CHANNEL, "note": 53},
    "pad-02": {"channel": PAD_CHANNEL, "note": 49},
    "pad-03": {"channel": PAD_CHANNEL, "note": 44},
    "pad-04": {"channel": PAD_CHANNEL, "note": 52},
    "pad-05": {"channel": PAD_CHANNEL, "note": 41},
    "pad-06": {"channel": PAD_CHANNEL, "note": 43},
    "pad-07": {"channel": PAD_CHANNEL, "note": 37},
    "pad-08": {"channel": PAD_CHANNEL, "note": 51},
    "pad-09": {"channel": PAD_CHANNEL, "note": 42},
    "pad-10": {"channel": PAD_CHANNEL, "note": 47},
    "pad-11": {"channel": PAD_CHANNEL, "note": 38},
    "pad-12": {"channel": PAD_CHANNEL, "note": 36},
    "pad-13": {"channel": PAD_CHANNEL, "note": 45},
    "pad-14": {"channel": PAD_CHANNEL, "note": 40},
    "pad-15": {"channel": PAD_CHANNEL, "note": 46},
    "pad-16": {"channel": PAD_CHANNEL, "note": 48},
    "pad-17": {"channel": PAD_CHANNEL, "note": 50},
    "pad-18": {"channel": PAD_CHANNEL, "note": 39},
    # --- 8 klawiszy RGB (kanał 15 / 0-idx 14) ---
    "key-01": {"channel": KEY_CHANNEL, "note": 54},
    "key-02": {"channel": KEY_CHANNEL, "note": 55},
    "key-03": {"channel": KEY_CHANNEL, "note": 56},
    "key-04": {"channel": KEY_CHANNEL, "note": 57},
    "key-05": {"channel": KEY_CHANNEL, "note": 58},
    "key-06": {"channel": KEY_CHANNEL, "note": 59},
    "key-07": {"channel": KEY_CHANNEL, "note": 60},
    "key-08": {"channel": KEY_CHANNEL, "note": 61},
}


def _clone_default() -> dict[str, dict]:
    return {k: dict(v) for k, v in DEFAULT_MAPPING.items()}


class MappingStore:
    """id -> {'channel': int, 'note': int}. Startuje z DEFAULT_MAPPING."""

    def __init__(self, path: Path = STORE_PATH):
        self.path = path
        self._fwd: dict[str, dict] = _clone_default()
        self.load()

    # ---------- io ----------

    def load(self):
        """Bierze defaulty i nakłada na nie ewentualne wpisy z mappings.json."""
        self._fwd = _clone_default()
        if self.path.exists():
            try:
                user = json.loads(self.path.read_text())
                for pad_id, m in user.items():
                    if isinstance(m, dict) and "channel" in m and "note" in m:
                        self._fwd[pad_id] = {"channel": int(m["channel"]), "note": int(m["note"])}
            except Exception:
                pass

    def save(self):
        self.path.write_text(json.dumps(self._fwd, indent=2, sort_keys=True))

    def reset_to_defaults(self):
        self._fwd = _clone_default()

    # ---------- queries ----------

    def get_note(self, pad_id: str) -> tuple[int, int] | None:
        m = self._fwd.get(pad_id)
        if not m:
            return None
        return m["channel"], m["note"]

    def find_pad(self, channel: int, note: int) -> str | None:
        for pad_id, m in self._fwd.items():
            if m["channel"] == channel and m["note"] == note:
                return pad_id
        return None

    def is_mapped(self, pad_id: str) -> bool:
        return pad_id in self._fwd

    def all(self) -> dict[str, dict]:
        return dict(self._fwd)

    # ---------- mutations ----------

    def learn(self, pad_id: str, channel: int, note: int):
        for existing_id in [k for k, v in self._fwd.items()
                            if v["channel"] == channel and v["note"] == note and k != pad_id]:
            del self._fwd[existing_id]
        self._fwd[pad_id] = {"channel": channel, "note": note}

    def unmap(self, pad_id: str):
        self._fwd.pop(pad_id, None)

    def clear(self):
        self._fwd.clear()
