"""Inspector panel: edycja channel/note/velocity/enabled dla wybranego output cell."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(n: int) -> str:
    octave = (n // 12) - 1
    return f"{NOTE_NAMES[n % 12]}{octave}"


class OutputEditor(QFrame):
    changed = Signal(str, dict)        # out_id, {field: new_value}
    unroute_requested = Signal(str)    # out_id

    def __init__(self):
        super().__init__()
        self.setObjectName("editor")
        self.setFrameShape(QFrame.StyledPanel)

        self._out_id: str | None = None
        self._block = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(8)

        title = QLabel("Output cell")
        title.setStyleSheet("font-weight: bold; font-size: 13px; color: #ffffff;")
        outer.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(6)

        self.id_label = QLabel("—")
        self.id_label.setStyleSheet("color: #88c97a; font-family: Menlo, monospace;")
        form.addRow("ID", self.id_label)

        self.source_label = QLabel("—")
        self.source_label.setStyleSheet("color: #cccccc; font-family: Menlo, monospace;")
        form.addRow("Source pad", self.source_label)

        self.enabled_chk = QCheckBox("send MIDI on trigger")
        self.enabled_chk.toggled.connect(self._on_enabled)
        form.addRow("Enabled", self.enabled_chk)

        self.channel_spin = QSpinBox()
        self.channel_spin.setRange(1, 16)
        self.channel_spin.valueChanged.connect(self._on_channel)
        form.addRow("Channel", self.channel_spin)

        note_row = QHBoxLayout()
        self.note_spin = QSpinBox()
        self.note_spin.setRange(0, 127)
        self.note_spin.valueChanged.connect(self._on_note)
        note_row.addWidget(self.note_spin)

        self.note_name_label = QLabel("—")
        self.note_name_label.setStyleSheet("color: #6cc8ff; font-family: Menlo, monospace; padding-left: 8px;")
        note_row.addWidget(self.note_name_label, 1)
        form.addRow("Note", note_row)

        self.velocity_spin = QSpinBox()
        self.velocity_spin.setRange(1, 127)
        self.velocity_spin.valueChanged.connect(self._on_velocity)
        form.addRow("Velocity", self.velocity_spin)

        outer.addLayout(form)

        btn_row = QHBoxLayout()
        self.unroute_btn = QPushButton("Unroute")
        self.unroute_btn.clicked.connect(self._on_unroute)
        btn_row.addWidget(self.unroute_btn)
        btn_row.addStretch(1)
        outer.addLayout(btn_row)

        outer.addStretch(1)

        self.setEnabled(False)

    # ---------- public ----------

    def select(self, out_id: str | None, cell):
        self._block = True
        try:
            self._out_id = out_id
            if out_id is None or cell is None:
                self.id_label.setText("—")
                self.source_label.setText("—")
                self.enabled_chk.setChecked(False)
                self.channel_spin.setValue(1)
                self.note_spin.setValue(60)
                self.note_name_label.setText("—")
                self.velocity_spin.setValue(100)
                self.setEnabled(False)
                return
            self.setEnabled(True)
            self.id_label.setText(out_id)
            self.source_label.setText(cell.source_pad or "(none)")
            self.enabled_chk.setChecked(cell.enabled)
            self.channel_spin.setValue(int(cell.channel) + 1)
            self.note_spin.setValue(int(cell.note))
            self.note_name_label.setText(note_name(int(cell.note)))
            self.velocity_spin.setValue(int(cell.velocity))
        finally:
            self._block = False

    def refresh_source(self, source_pad: str | None):
        self.source_label.setText(source_pad or "(none)")

    # ---------- handlers ----------

    def _emit(self, field: str, value):
        if self._block or not self._out_id:
            return
        self.changed.emit(self._out_id, {field: value})

    def _on_enabled(self, on: bool):
        self._emit("enabled", bool(on))

    def _on_channel(self, v: int):
        self._emit("channel", int(v) - 1)

    def _on_note(self, v: int):
        self.note_name_label.setText(note_name(int(v)))
        self._emit("note", int(v))

    def _on_velocity(self, v: int):
        self._emit("velocity", int(v))

    def _on_unroute(self):
        if self._out_id:
            self.unroute_requested.emit(self._out_id)
