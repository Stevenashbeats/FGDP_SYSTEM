# FGDP_SYSTEM

Sampler / MIDI mapper dla **Yamaha FGDP-50** — finger drum pad z konwersją hardware MIDI na własny layout 4×4 (MPC style) z edytowalnymi voice'ami per cell.

Pisany w PySide6, w trakcie aktywnej rozbudowy. Kolejne iteracje: audio engine, sample loader, choke groups.

## Stan

- Parsowanie SVG layoutu FGDP-50 → klikalne pady (18 czarnych + 8 RGB)
- MIDI in/out via `mido` + `python-rtmidi`
- **LEARN** — uzbrój pad w GUI, naciśnij hardware → zapisuje mapping
- **ROUTE** — wpinasz pad/key FGDP do output cell w siatce 4×4
- **Editor** per output cell — channel, note, velocity, enabled
- Preset system — zapis/odczyt całego stanu (mapping + outputs)
- MIDI monitor (live log)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Wymagany Python 3.10+ (dataclasses + nowoczesne type hints).

## Struktura

| plik | rola |
|---|---|
| `app.py` | main window, mode handling, glue |
| `pad_view.py` | QGraphicsScene z FGDP padami z SVG |
| `output_view.py` | siatka 4×4 output cells |
| `output_map.py` | `OutputBank` + `OutputCell` (voice + routing) |
| `output_editor.py` | inspector panel po prawej |
| `mappings.py` | input mapping FGDP → pad_id |
| `midi_engine.py` | wrapper na `mido` |
| `svg_loader.py` | parser ścieżek SVG → `QPainterPath` |
| `presets.py` | zapis/odczyt presetów (mapping + outputs) |
| `presets/` | nazwane presety (JSON) |

## Pipeline

```
hardware MIDI in
   │
   ▼
mapping (channel,note) ──► pad_id  (pad-01..pad-18, key-01..key-08)
                              │
                              ▼
                       routing (cell.source_pad)
                              │
                              ▼
                          output cell (out-01..out-16, MPC layout)
                              │
                              ▼
                    voice cfg (channel/note/velocity/enabled)
                              │
                              ▼
                          MIDI OUT
```
