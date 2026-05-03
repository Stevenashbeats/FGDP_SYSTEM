"""FGDP Sampler — iteracja 2: MIDI Monitor + Learn + Output Bank + Editor.

Pipeline:
  hardware FGDP MIDI in -> mapping (channel,note) -> fgdp_id (pad/key)
                                                   |
                                                   v
                                  routing (cell.source_pad) -> output cell
                                                                    |
                                                                    v
                                                    voice cfg (cell channel/note/vel)
                                                                    |
                                                                    v
                                                              MIDI OUT port

  klik output cell w PLAY -> trigger voice (jak wyżej) + selekcja w editorze

Tryby (mutually exclusive):
  PLAY   : klik gra, klik celli zaznacza je do edycji
  LEARN  : klik pad GUI -> uzbrojony, następna nuta hardware -> mapping
  ROUTE  : klik output cell -> uzbrojony, następny pad -> set route
"""

import sys
from datetime import datetime
from pathlib import Path

import mido
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from mappings import MappingStore
from midi_engine import MidiEngine
from output_editor import OutputEditor, note_name
from output_map import OutputBank
from output_view import OutputView
from pad_view import PadView
from paths import bundle_dir
from presets import list_presets, load_preset, save_preset

SVG_PATH = bundle_dir() / "PADS DESIGN_01.svg"

STYLE = """
QMainWindow, QWidget { background: #121212; color: #e5e5e5; }
QLabel { color: #cccccc; }
QComboBox {
    background: #1e1e1e; color: #e5e5e5; border: 1px solid #333;
    padding: 4px 8px; border-radius: 4px;
}
QComboBox QAbstractItemView { background: #1e1e1e; color: #e5e5e5; selection-background-color: #2a3a4a; }
QPushButton {
    background: #1e1e1e; color: #e5e5e5; border: 1px solid #333;
    padding: 4px 12px; border-radius: 4px;
}
QPushButton:hover { background: #2a2a2a; }
QPushButton:checked { background: #5a4a10; border-color: #ffd24d; color: #ffd24d; }
QPushButton:disabled { color: #555; border-color: #222; }
QSpinBox, QCheckBox {
    background: #1e1e1e; color: #e5e5e5; border: 1px solid #333;
    padding: 2px 4px; border-radius: 4px; min-width: 60px;
}
QCheckBox { background: transparent; border: none; padding: 0; }
QSpinBox::up-button, QSpinBox::down-button { background: #2a2a2a; }
QFrame#editor {
    background: #161616; border: 1px solid #2a2a2a; border-radius: 6px;
}
QPlainTextEdit {
    background: #0a0a0a; color: #cfd6dc; border: 1px solid #222;
    font-family: Menlo, Monaco, Consolas, monospace; font-size: 12px;
}
QSplitter::handle { background: #1a1a1a; }
QSplitter::handle:horizontal { width: 4px; }
QSplitter::handle:vertical { height: 4px; }
#status { padding: 4px 8px; border: 1px solid #222; border-radius: 4px; background: #161616; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FGDP Sampler — Editor")
        self.resize(1500, 880)

        self.midi = MidiEngine()
        self.midi.message_in.connect(self.on_midi_in)

        self.mapping = MappingStore()
        self.bank = OutputBank()

        self.armed_pad: str | None = None
        self.armed_output: str | None = None
        self.selected_output: str | None = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # --- urządzenia ---
        dev_row = QHBoxLayout()
        dev_row.addWidget(QLabel("MIDI IN"))
        self.in_combo = QComboBox()
        self.in_combo.currentTextChanged.connect(self.on_in_changed)
        dev_row.addWidget(self.in_combo, 1)

        dev_row.addWidget(QLabel("MIDI OUT"))
        self.out_combo = QComboBox()
        self.out_combo.currentTextChanged.connect(self.on_out_changed)
        dev_row.addWidget(self.out_combo, 1)

        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh_devices)
        dev_row.addWidget(refresh)

        layout.addLayout(dev_row)

        # --- presety ---
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("PRESET"))
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(220)
        preset_row.addWidget(self.preset_combo, 1)

        load_preset_btn = QPushButton("Load")
        load_preset_btn.clicked.connect(self.on_load_preset)
        preset_row.addWidget(load_preset_btn)

        save_preset_btn = QPushButton("Save as new")
        save_preset_btn.clicked.connect(self.on_save_preset)
        preset_row.addWidget(save_preset_btn)

        preset_row.addStretch(1)
        layout.addLayout(preset_row)

        # --- akcje ---
        action_row = QHBoxLayout()

        self.learn_btn = QPushButton("LEARN")
        self.learn_btn.setCheckable(True)
        self.learn_btn.toggled.connect(self.on_learn_toggled)
        action_row.addWidget(self.learn_btn)

        self.route_btn = QPushButton("ROUTE")
        self.route_btn.setCheckable(True)
        self.route_btn.toggled.connect(self.on_route_toggled)
        action_row.addWidget(self.route_btn)

        action_row.addSpacing(12)

        save_map_btn = QPushButton("Save mapping")
        save_map_btn.clicked.connect(self.on_save_mapping)
        action_row.addWidget(save_map_btn)

        save_bank_btn = QPushButton("Save outputs")
        save_bank_btn.clicked.connect(self.on_save_bank)
        action_row.addWidget(save_bank_btn)

        reset_map_btn = QPushButton("Reset mapping")
        reset_map_btn.clicked.connect(self.on_reset_mapping)
        action_row.addWidget(reset_map_btn)

        reset_bank_btn = QPushButton("Reset outputs")
        reset_bank_btn.clicked.connect(self.on_reset_bank)
        action_row.addWidget(reset_bank_btn)

        action_row.addStretch(1)

        self.status = QLabel("PLAY mode")
        self.status.setObjectName("status")
        action_row.addWidget(self.status)

        clear_log = QPushButton("Clear log")
        clear_log.clicked.connect(lambda: self.log.clear())
        action_row.addWidget(clear_log)

        layout.addLayout(action_row)

        # --- main split (PadView | OutputView | Editor) ---
        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)

        self.pad_view = PadView(SVG_PATH)
        self.pad_view.signals.pressed.connect(self.on_pad_pressed)
        self.pad_view.signals.released.connect(self.on_pad_released)
        split.addWidget(self.pad_view)

        self.output_view = OutputView()
        self.output_view.signals.pressed.connect(self.on_output_pressed)
        self.output_view.signals.released.connect(self.on_output_released)
        split.addWidget(self.output_view)

        self.editor = OutputEditor()
        self.editor.changed.connect(self.on_editor_changed)
        self.editor.unroute_requested.connect(self.on_unroute_requested)
        split.addWidget(self.editor)

        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 0)
        split.setSizes([520, 520, 260])
        layout.addWidget(split, 1)

        # --- monitor ---
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1000)
        self.log.setMinimumHeight(160)
        layout.addWidget(self.log, 0)

        self.setStyleSheet(STYLE)

        self.refresh_devices()
        self._refresh_presets()
        self._refresh_pad_mapped_state()
        self._refresh_all_cells()
        self.log_line(
            f"ready. mapped: {len(self.mapping.all())}  outputs: {len(self.bank.all())}"
        )

    # ---------- presety ----------

    def _refresh_presets(self):
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self._presets = list_presets()
        for p in self._presets:
            self.preset_combo.addItem(p["name"])
        self.preset_combo.blockSignals(False)

    def on_load_preset(self):
        idx = self.preset_combo.currentIndex()
        if idx < 0 or idx >= len(self._presets):
            return
        p = self._presets[idx]
        name = load_preset(p["file"], self.mapping, self.bank)
        self._refresh_pad_mapped_state()
        self._refresh_all_cells()
        if self.selected_output:
            self.editor.select(self.selected_output, self.bank.get(self.selected_output))
        self.log_line(f"-- loaded preset: {name}")

    def on_save_preset(self):
        name, ok = QInputDialog.getText(self, "Save preset", "Nazwa presetu:")
        if not ok or not name.strip():
            return
        path = save_preset(name.strip(), self.mapping, self.bank)
        self._refresh_presets()
        self.preset_combo.setCurrentIndex(self.preset_combo.count() - 1)
        self.log_line(f"-- saved preset: {name.strip()} -> {path.name}")

    # ---------- urządzenia ----------

    def refresh_devices(self):
        for combo, names in (
            (self.in_combo, MidiEngine.list_inputs()),
            (self.out_combo, MidiEngine.list_outputs()),
        ):
            combo.blockSignals(True)
            current = combo.currentText()
            combo.clear()
            combo.addItem("(none)")
            for n in names:
                combo.addItem(n)
            idx = combo.findText(current)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)
        self.log_line(f"devices: in={len(MidiEngine.list_inputs())}, out={len(MidiEngine.list_outputs())}")

    def on_in_changed(self, name: str):
        try:
            self.midi.open_input(None if name == "(none)" else name)
            self.log_line(f"-- IN  -> {name}")
        except Exception as e:
            self.log_line(f"!! IN  error: {e}")

    def on_out_changed(self, name: str):
        try:
            self.midi.open_output(None if name == "(none)" else name)
            self.log_line(f"-- OUT -> {name}")
        except Exception as e:
            self.log_line(f"!! OUT error: {e}")

    # ---------- mode handling ----------

    def on_learn_toggled(self, on: bool):
        if on:
            if self.route_btn.isChecked():
                self.route_btn.blockSignals(True)
                self.route_btn.setChecked(False)
                self.route_btn.blockSignals(False)
                self._disarm_output()
            self.status.setText("LEARN — kliknij pad, potem zagraj na hardware")
        else:
            self._disarm_pad()
            self._update_status_idle()

    def on_route_toggled(self, on: bool):
        if on:
            if self.learn_btn.isChecked():
                self.learn_btn.blockSignals(True)
                self.learn_btn.setChecked(False)
                self.learn_btn.blockSignals(False)
                self._disarm_pad()
            self.status.setText("ROUTE — kliknij output cell, potem pad")
        else:
            self._disarm_output()
            self._update_status_idle()

    def _update_status_idle(self):
        if self.learn_btn.isChecked():
            self.status.setText("LEARN — kliknij kolejny pad")
        elif self.route_btn.isChecked():
            self.status.setText("ROUTE — kliknij output cell")
        else:
            self.status.setText("PLAY mode")

    # ---------- learn ----------

    def _arm_pad(self, pad_id: str):
        self._disarm_pad()
        self.armed_pad = pad_id
        item = self.pad_view.items_by_id.get(pad_id)
        if item is not None:
            item.set_armed(True)
        self.status.setText(f"LEARN — czeka na MIDI dla [{pad_id}]")
        self.log_line(f"-- armed pad {pad_id}")

    def _disarm_pad(self):
        if self.armed_pad:
            item = self.pad_view.items_by_id.get(self.armed_pad)
            if item is not None:
                item.set_armed(False)
        self.armed_pad = None

    def _learn(self, channel: int, note: int):
        if not self.armed_pad:
            return
        pad_id = self.armed_pad
        self.mapping.learn(pad_id, channel, note)
        self.log_line(f"-- learned {pad_id} <- ch={channel + 1} note={note}")
        self._disarm_pad()
        self._refresh_pad_mapped_state()
        self._update_status_idle()

    # ---------- route ----------

    def _arm_output(self, out_id: str):
        self._disarm_output()
        self.armed_output = out_id
        cell = self.output_view.cells.get(out_id)
        if cell is not None:
            cell.set_armed(True)
        self.status.setText(f"ROUTE — czeka na pad dla [{out_id}]")
        self.log_line(f"-- armed output {out_id}")

    def _disarm_output(self):
        if self.armed_output:
            cell = self.output_view.cells.get(self.armed_output)
            if cell is not None:
                cell.set_armed(False)
        self.armed_output = None

    def _route(self, fgdp_id: str):
        if not self.armed_output:
            return
        out_id = self.armed_output
        self.bank.set_route(fgdp_id, out_id)
        self.log_line(f"-- routed {fgdp_id} -> {out_id}")
        self._disarm_output()
        self._refresh_all_cells()
        if self.selected_output == out_id:
            self.editor.refresh_source(fgdp_id)
        self._update_status_idle()

    # ---------- editor ----------

    def on_editor_changed(self, out_id: str, fields: dict):
        self.bank.update(out_id, **fields)
        cell = self.output_view.cells.get(out_id)
        bank_cell = self.bank.get(out_id)
        if cell is not None and bank_cell is not None:
            cell.set_voice_info(self._voice_label(bank_cell), bank_cell.enabled)
        self.log_line(f"-- edit {out_id} {fields}")

    def on_unroute_requested(self, out_id: str):
        src = self.bank.get_source(out_id)
        if not src:
            return
        self.bank.unroute_output(out_id)
        self.log_line(f"-- unrouted {out_id} (was {src})")
        self._refresh_all_cells()
        self.editor.refresh_source(None)

    def _select_output(self, out_id: str | None):
        if self.selected_output and self.selected_output != out_id:
            prev = self.output_view.cells.get(self.selected_output)
            if prev is not None:
                prev.set_selected(False)
        self.selected_output = out_id
        if out_id is None:
            self.editor.select(None, None)
            return
        cell = self.output_view.cells.get(out_id)
        if cell is not None:
            cell.set_selected(True)
        self.editor.select(out_id, self.bank.get(out_id))

    # ---------- save / reset ----------

    def on_save_mapping(self):
        self.mapping.save()
        self.log_line(f"-- saved mapping ({len(self.mapping.all())}) -> {self.mapping.path.name}")

    def on_save_bank(self):
        self.bank.save()
        self.log_line(f"-- saved outputs ({len(self.bank.all())}) -> {self.bank.path.name}")

    def on_reset_mapping(self):
        self.mapping.reset_to_defaults()
        self._refresh_pad_mapped_state()
        self.log_line(f"-- mapping reset ({len(self.mapping.all())})")

    def on_reset_bank(self):
        self.bank.reset_to_defaults()
        self._refresh_all_cells()
        if self.selected_output:
            self.editor.select(self.selected_output, self.bank.get(self.selected_output))
        self.log_line(f"-- outputs reset ({len(self.bank.all())})")

    # ---------- refresh ----------

    def _refresh_pad_mapped_state(self):
        for pad_id, item in self.pad_view.items_by_id.items():
            item.set_mapped(self.mapping.is_mapped(pad_id))

    def _refresh_all_cells(self):
        for out_id, item in self.output_view.cells.items():
            cell = self.bank.get(out_id)
            if cell is None:
                continue
            item.set_source(cell.source_pad or "")
            item.set_voice_info(self._voice_label(cell), cell.enabled)

    @staticmethod
    def _voice_label(cell) -> str:
        return f"{note_name(cell.note)}·c{cell.channel + 1}"

    # ---------- pad GUI ----------

    def on_pad_pressed(self, pad_id: str):
        if self.learn_btn.isChecked():
            self._arm_pad(pad_id)
            return
        if self.route_btn.isChecked() and self.armed_output:
            self._route(pad_id)
            return
        self._trigger_pad(pad_id, on=True, source="GUI")

    def on_pad_released(self, pad_id: str):
        if self.learn_btn.isChecked() or self.route_btn.isChecked():
            return
        self._trigger_pad(pad_id, on=False, source="GUI")

    def _trigger_pad(self, pad_id: str, on: bool, source: str, hw_velocity: int | None = None):
        out_id = self.bank.get_route(pad_id)
        if not out_id:
            if source == "GUI" and on:
                self.log_line(f"-- {pad_id} not routed")
            return
        cell = self.bank.get(out_id)
        if cell is None:
            return
        cell_item = self.output_view.cells.get(out_id)
        if cell_item is not None:
            cell_item.set_lit(on)
        if cell.enabled:
            self._send_voice(cell, on, tag=f"{pad_id}->{out_id}", logged=(source == "GUI"), hw_velocity=hw_velocity)
        elif on and source == "GUI":
            self.log_line(f"-- {out_id} disabled, no MIDI")

    def _send_voice(self, cell, on: bool, tag: str, logged: bool, hw_velocity: int | None = None):
        kind = "note_on" if on else "note_off"
        if not on:
            vel = 0
        elif getattr(cell, "velocity_mode", "fixed") == "passthrough" and hw_velocity is not None:
            vel = max(1, min(127, int(hw_velocity)))
        else:
            vel = cell.velocity
        msg = mido.Message(kind, channel=cell.channel, note=cell.note, velocity=vel)
        self.midi.send(msg)
        if logged:
            self.log_line(f"OUT  {self._fmt(msg)}   [{tag}]")

    # ---------- output GUI ----------

    def on_output_pressed(self, out_id: str):
        if self.route_btn.isChecked():
            self._arm_output(out_id)
            return
        self._select_output(out_id)
        cell = self.bank.get(out_id)
        if cell is None:
            return
        if cell.enabled:
            self._send_voice(cell, True, tag=out_id, logged=True)

    def on_output_released(self, out_id: str):
        if self.route_btn.isChecked():
            return
        cell = self.bank.get(out_id)
        if cell is None or not cell.enabled:
            return
        self._send_voice(cell, False, tag=out_id, logged=False)

    # ---------- MIDI in ----------

    def on_midi_in(self, msg):
        self.log_line(f"IN   {self._fmt(msg)}")
        if msg.type == "note_on" and msg.velocity > 0:
            if self.learn_btn.isChecked() and self.armed_pad:
                self._learn(msg.channel, msg.note)
                return
            pad_id = self.mapping.find_pad(msg.channel, msg.note)
            if not pad_id:
                return
            if self.route_btn.isChecked() and self.armed_output:
                self._route(pad_id)
                return
            item = self.pad_view.items_by_id.get(pad_id)
            if item is not None:
                item.set_midi(True)
            self._trigger_pad(pad_id, on=True, source="HW", hw_velocity=msg.velocity)
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            pad_id = self.mapping.find_pad(msg.channel, msg.note)
            if not pad_id:
                return
            item = self.pad_view.items_by_id.get(pad_id)
            if item is not None:
                item.set_midi(False)
            self._trigger_pad(pad_id, on=False, source="HW")

    # ---------- log ----------

    @staticmethod
    def _fmt(msg) -> str:
        if msg.type in ("note_on", "note_off"):
            return f"{msg.type:<8} ch={msg.channel + 1:<2} note={msg.note:<3} vel={msg.velocity:<3}"
        return str(msg)

    def log_line(self, text: str):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log.appendPlainText(f"{ts}  {text}")

    def closeEvent(self, e):
        self.midi.shutdown()
        super().closeEvent(e)


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
