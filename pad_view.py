"""QGraphicsView z padami i klawiszami parsowanymi z SVG."""

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
)

from svg_loader import load_items

VIEW_W = 165
VIEW_H = 115

STROKE_DEFAULT = QColor("#cccccc")
STROKE_HOVER = QColor("#ffffff")
STROKE_ACTIVE = QColor("#6cc8ff")
STROKE_ARMED = QColor("#ffd24d")
STROKE_MAPPED = QColor("#88c97a")
FILL_HOVER = QColor(108, 200, 255, 46)
FILL_ACTIVE = QColor(108, 200, 255, 115)
FILL_ARMED = QColor(255, 210, 77, 110)
KEY_DEFAULT = QColor("#cccccc")
KEY_HOVER = QColor("#ffffff")
KEY_ACTIVE = QColor("#6cc8ff")
KEY_ARMED = QColor("#ffd24d")
KEY_MAPPED = QColor("#88c97a")


class PadSignals(QObject):
    pressed = Signal(str)
    released = Signal(str)


class PadItem(QGraphicsPathItem):
    def __init__(self, pad_id: str, qpath, kind: str, signals: PadSignals):
        super().__init__(qpath)
        self.pad_id = pad_id
        self.kind = kind
        self.signals = signals
        self._hover = False
        self._mouse = False
        self._midi = False
        self._armed = False
        self._mapped = False
        self.setAcceptHoverEvents(True)
        self._refresh()

    def _refresh(self):
        active = self._mouse or self._midi
        if self.kind == "stroke":
            if self._armed:
                color = STROKE_ARMED
            elif active:
                color = STROKE_ACTIVE
            elif self._hover:
                color = STROKE_HOVER
            elif self._mapped:
                color = STROKE_MAPPED
            else:
                color = STROKE_DEFAULT
            pen = QPen(color)
            pen.setWidthF(0.992375)
            pen.setCosmetic(False)
            self.setPen(pen)
            if self._armed:
                self.setBrush(QBrush(FILL_ARMED))
            elif active:
                self.setBrush(QBrush(FILL_ACTIVE))
            elif self._hover:
                self.setBrush(QBrush(FILL_HOVER))
            else:
                self.setBrush(QBrush(Qt.transparent))
        else:
            self.setPen(QPen(Qt.transparent))
            if self._armed:
                self.setBrush(QBrush(KEY_ARMED))
            elif active:
                self.setBrush(QBrush(KEY_ACTIVE))
            elif self._hover:
                self.setBrush(QBrush(KEY_HOVER))
            elif self._mapped:
                self.setBrush(QBrush(KEY_MAPPED))
            else:
                self.setBrush(QBrush(KEY_DEFAULT))

    def hoverEnterEvent(self, e):
        self._hover = True
        self._refresh()
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        self._hover = False
        self._refresh()
        super().hoverLeaveEvent(e)

    def mousePressEvent(self, e):
        self._mouse = True
        self._refresh()
        self.signals.pressed.emit(self.pad_id)
        e.accept()

    def mouseReleaseEvent(self, e):
        self._mouse = False
        self._refresh()
        self.signals.released.emit(self.pad_id)
        e.accept()

    def set_midi(self, on: bool):
        self._midi = on
        self._refresh()

    def set_armed(self, on: bool):
        self._armed = on
        self._refresh()

    def set_mapped(self, on: bool):
        self._mapped = on
        self._refresh()


class PadView(QGraphicsView):
    def __init__(self, svg_path):
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor("#121212")))
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.signals = PadSignals()
        self.items_by_id: dict[str, PadItem] = {}

        for pad_id, qpath, kind in load_items(svg_path):
            item = PadItem(pad_id, qpath, kind, self.signals)
            self._scene.addItem(item)
            self.items_by_id[pad_id] = item

        self._scene.setSceneRect(0, 0, VIEW_W, VIEW_H)

    def resizeEvent(self, e):
        self.fitInView(0, 0, VIEW_W, VIEW_H, Qt.KeepAspectRatio)
        super().resizeEvent(e)

    def showEvent(self, e):
        self.fitInView(0, 0, VIEW_W, VIEW_H, Qt.KeepAspectRatio)
        super().showEvent(e)
