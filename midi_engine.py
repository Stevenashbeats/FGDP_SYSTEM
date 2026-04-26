"""Cienki wrapper na mido. Sygnał message_in emitowany z wątku rtmidi -> Qt queued."""

import mido
from PySide6.QtCore import QObject, Signal


class MidiEngine(QObject):
    message_in = Signal(object)  # mido.Message

    def __init__(self):
        super().__init__()
        self._in_port = None
        self._out_port = None

    @staticmethod
    def list_inputs() -> list[str]:
        try:
            return mido.get_input_names()
        except Exception:
            return []

    @staticmethod
    def list_outputs() -> list[str]:
        try:
            return mido.get_output_names()
        except Exception:
            return []

    def open_input(self, name: str | None):
        self.close_input()
        if name:
            self._in_port = mido.open_input(name, callback=self._on_msg)

    def open_output(self, name: str | None):
        self.close_output()
        if name:
            self._out_port = mido.open_output(name)

    def close_input(self):
        if self._in_port is not None:
            try:
                self._in_port.close()
            finally:
                self._in_port = None

    def close_output(self):
        if self._out_port is not None:
            try:
                self._out_port.close()
            finally:
                self._out_port = None

    def send(self, msg: mido.Message):
        if self._out_port is not None:
            self._out_port.send(msg)

    def _on_msg(self, msg: mido.Message):
        self.message_in.emit(msg)

    def shutdown(self):
        self.close_input()
        self.close_output()
