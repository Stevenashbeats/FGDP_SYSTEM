"""Output bank: 16 cell w stylu MPC, każdy ma własny voice (MIDI msg) i routing.

Każdy OutputCell trzyma:
  - voice: channel/note/velocity wysyłane gdy cell jest triggerowany
  - source_pad: który FGDP pad wyzwala ten cell (routing 1:1)
  - enabled: czy cell w ogóle wysyła MIDI
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

GRID_COLS = 4
GRID_ROWS = 4
GRID_SIZE = GRID_COLS * GRID_ROWS  # 16

OUTPUT_IDS: tuple[str, ...] = tuple(f"out-{i:02d}" for i in range(1, GRID_SIZE + 1))

STORE_PATH = Path(__file__).parent / "outputs.json"


@dataclass
class OutputCell:
    channel: int = 0           # 0..15  (UI pokaże +1)
    note: int = 60             # 0..127
    velocity: int = 100        # 1..127  (używane gdy velocity_mode == "fixed")
    velocity_mode: str = "fixed"   # "fixed" | "passthrough"
    enabled: bool = True
    source_pad: str | None = None  # routing source (FGDP pad/key id)


# Defaults: każdy cell ma kanał 1, noty od C2 (36) w górę, velocity 100,
# routing pad-01..pad-16 -> out-01..out-16.
def _default_cells() -> dict[str, OutputCell]:
    return {
        f"out-{i:02d}": OutputCell(
            channel=0,
            note=35 + i,  # out-01 -> 36 (C2), out-02 -> 37, ...
            velocity=100,
            enabled=True,
            source_pad=f"pad-{i:02d}",
        )
        for i in range(1, GRID_SIZE + 1)
    }


def mpc_position(out_id: str) -> tuple[int, int]:
    """Layout MPC: 1 = lewo-dół, 16 = prawo-góra. Zwraca (col, row_from_top)."""
    n = int(out_id.split("-")[1])
    col = (n - 1) % GRID_COLS
    row_from_bottom = (n - 1) // GRID_COLS
    row_from_top = (GRID_ROWS - 1) - row_from_bottom
    return col, row_from_top


class OutputBank:
    def __init__(self, path: Path = STORE_PATH):
        self.path = path
        self._cells: dict[str, OutputCell] = _default_cells()
        self.load()

    # ---------- io ----------

    def load(self):
        self._cells = _default_cells()
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
            if not isinstance(data, dict):
                return
            for oid, d in data.items():
                if oid not in self._cells or not isinstance(d, dict):
                    continue
                cell = self._cells[oid]
                for k, v in d.items():
                    if hasattr(cell, k):
                        setattr(cell, k, v)
        except Exception:
            pass

    def save(self):
        data = {oid: asdict(c) for oid, c in self._cells.items()}
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True))

    def reset_to_defaults(self):
        self._cells = _default_cells()

    # ---------- queries ----------

    def get(self, out_id: str) -> OutputCell | None:
        return self._cells.get(out_id)

    def all(self) -> dict[str, OutputCell]:
        return dict(self._cells)

    def items(self):
        return self._cells.items()

    def get_route(self, fgdp_id: str) -> str | None:
        for oid, c in self._cells.items():
            if c.source_pad == fgdp_id:
                return oid
        return None

    def get_source(self, out_id: str) -> str | None:
        c = self._cells.get(out_id)
        return c.source_pad if c else None

    # ---------- mutations ----------

    def update(self, out_id: str, **fields):
        c = self._cells.get(out_id)
        if not c:
            return
        for k, v in fields.items():
            if hasattr(c, k):
                setattr(c, k, v)

    def set_route(self, fgdp_id: str, out_id: str):
        # 1:1 — usuń istniejące przypisanie tego pad
        for oid, c in self._cells.items():
            if c.source_pad == fgdp_id and oid != out_id:
                c.source_pad = None
        target = self._cells.get(out_id)
        if target is not None:
            target.source_pad = fgdp_id

    def unroute_pad(self, fgdp_id: str):
        for c in self._cells.values():
            if c.source_pad == fgdp_id:
                c.source_pad = None

    def unroute_output(self, out_id: str):
        c = self._cells.get(out_id)
        if c is not None:
            c.source_pad = None
