"""Parsuje PADS DESIGN_01.svg i zwraca QPainterPath dla każdego pada/klawisza."""

import re
from pathlib import Path
from xml.etree import ElementTree as ET

from PySide6.QtGui import QPainterPath

NUM_RE = re.compile(r'-?\d*\.?\d+(?:[eE][-+]?\d+)?')
SVG_NS = "http://www.w3.org/2000/svg"


def _parse_d(d: str) -> QPainterPath:
    path = QPainterPath()
    tokens = re.split(r'(?=[MLHVCSQTAZmlhvcsqtaz])', d)
    cx = cy = sx = sy = 0.0
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        cmd = tok[0]
        nums = [float(n) for n in NUM_RE.findall(tok[1:])]
        if cmd == 'M':
            for i in range(0, len(nums), 2):
                x, y = nums[i], nums[i + 1]
                if i == 0:
                    path.moveTo(x, y)
                    sx, sy = x, y
                else:
                    path.lineTo(x, y)
                cx, cy = x, y
        elif cmd == 'L':
            for i in range(0, len(nums), 2):
                x, y = nums[i], nums[i + 1]
                path.lineTo(x, y)
                cx, cy = x, y
        elif cmd == 'H':
            for x in nums:
                path.lineTo(x, cy)
                cx = x
        elif cmd == 'V':
            for y in nums:
                path.lineTo(cx, y)
                cy = y
        elif cmd == 'C':
            for i in range(0, len(nums), 6):
                x1, y1, x2, y2, x, y = nums[i:i + 6]
                path.cubicTo(x1, y1, x2, y2, x, y)
                cx, cy = x, y
        elif cmd in ('Z', 'z'):
            path.closeSubpath()
            cx, cy = sx, sy
    return path


# Każdy pad to jeden lub kilka subpathów (1..27 z dużej ścieżki źródłowej).
PAD_GROUPS = (
    [("pad-01", list(range(0, 4)))]
    + [("pad-02", list(range(4, 8)))]
    + [("pad-03", list(range(8, 12)))]
    + [(f"pad-{i:02d}", [8 + i]) for i in range(4, 19)]
)


def load_items(svg_path: str | Path):
    """Zwraca listę krotek (id, QPainterPath, kind) gdzie kind in {'stroke','fill'}."""
    tree = ET.parse(str(svg_path))
    root = tree.getroot()
    paths = root.findall(f"{{{SVG_NS}}}path")

    items: list[tuple[str, QPainterPath, str]] = []

    pad_d = paths[0].get("d", "")
    subs = [s.strip() for s in re.split(r'(?=M)', pad_d) if s.strip()]
    for name, idxs in PAD_GROUPS:
        d = " ".join(subs[i] for i in idxs)
        items.append((name, _parse_d(d), "stroke"))

    keys = []
    for p in paths[1:]:
        d = p.get("d", "")
        m = re.match(r'M([\d.\-]+)', d)
        x = float(m.group(1)) if m else 0.0
        keys.append((x, d))
    keys.sort(key=lambda k: k[0])
    for i, (_, d) in enumerate(keys, start=1):
        items.append((f"key-{i:02d}", _parse_d(d), "fill"))

    return items
