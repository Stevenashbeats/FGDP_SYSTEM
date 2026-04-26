"""QGraphicsView z siatką 4x4 output cells (MPC layout)."""

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
)

from output_map import GRID_COLS, GRID_ROWS, OUTPUT_IDS, mpc_position
from pad_view import VIEW_W, VIEW_H

CELL_SIZE = 110.0
CELL_GAP = 12.0
CELL_RADIUS = 10.0

BG = QColor("#0e0e0e")
CELL_EMPTY = QColor("#161616")
CELL_HOVER = QColor("#222a32")
CELL_HIT = QColor("#1f4060")
CELL_ARMED = QColor("#5a4a10")

BORDER_EMPTY = QColor("#3a3a3a")
BORDER_ROUTED = QColor("#88c97a")
BORDER_HOVER = QColor("#ffffff")
BORDER_HIT = QColor("#6cc8ff")
BORDER_ARMED = QColor("#ffd24d")
BORDER_SELECTED = QColor("#ff8c42")
BORDER_DISABLED = QColor("#5a2a2a")

LABEL_COLOR = QColor("#cccccc")
SUBLABEL_COLOR = QColor("#7c8794")
SUBLABEL_VOICE_COLOR = QColor("#9fb2c4")


class CellSignals(QObject):
    pressed = Signal(str)
    released = Signal(str)


class OutputCellItem(QGraphicsRectItem):
    def __init__(self, out_id: str, mpc_number: int, signals: CellSignals):
        super().__init__(0, 0, CELL_SIZE, CELL_SIZE)
        self.out_id = out_id
        self.mpc_number = mpc_number
        self.signals = signals

        self._hover = False
        self._mouse = False
        self._lit = False
        self._armed = False
        self._selected = False
        self._routed = False
        self._enabled = True

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)

        self._number = QGraphicsTextItem(str(mpc_number), parent=self)
        self._number.setFont(QFont("Menlo", 22, QFont.Bold))
        self._number.setDefaultTextColor(LABEL_COLOR)
        nbr = self._number.boundingRect()
        self._number.setPos((CELL_SIZE - nbr.width()) / 2, 8)

        self._source = QGraphicsTextItem("", parent=self)
        self._source.setFont(QFont("Menlo", 8))
        self._source.setDefaultTextColor(SUBLABEL_COLOR)

        self._voice = QGraphicsTextItem("", parent=self)
        self._voice.setFont(QFont("Menlo", 9, QFont.Bold))
        self._voice.setDefaultTextColor(SUBLABEL_VOICE_COLOR)

        self._reposition_subs()
        self._refresh()

    # ---------- painting ----------

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawRoundedRect(self.rect(), CELL_RADIUS, CELL_RADIUS)

    def _reposition_subs(self):
        sbr = self._source.boundingRect()
        self._source.setPos((CELL_SIZE - sbr.width()) / 2, CELL_SIZE - sbr.height() - 22)
        vbr = self._voice.boundingRect()
        self._voice.setPos((CELL_SIZE - vbr.width()) / 2, CELL_SIZE - vbr.height() - 8)

    def _refresh(self):
        if self._armed:
            fill = CELL_ARMED
            border = BORDER_ARMED
            border_w = 3.0
        elif self._lit or self._mouse:
            fill = CELL_HIT
            border = BORDER_HIT
            border_w = 2.5
        elif self._selected:
            fill = CELL_EMPTY
            border = BORDER_SELECTED
            border_w = 2.5
        elif self._hover:
            fill = CELL_HOVER
            border = BORDER_HOVER
            border_w = 1.5
        else:
            fill = CELL_EMPTY
            if not self._enabled:
                border = BORDER_DISABLED
            elif self._routed:
                border = BORDER_ROUTED
            else:
                border = BORDER_EMPTY
            border_w = 1.5
        self.setBrush(QBrush(fill))
        pen = QPen(border)
        pen.setWidthF(border_w)
        self.setPen(pen)
        self.update()

    # ---------- state ----------

    def set_voice_info(self, voice_text: str, enabled: bool):
        self._voice.setPlainText(voice_text)
        self._enabled = enabled
        self._reposition_subs()
        self._refresh()

    def set_source(self, source_label: str):
        self._source.setPlainText(source_label)
        self._routed = bool(source_label)
        self._reposition_subs()
        self._refresh()

    def set_lit(self, on: bool):
        self._lit = on
        self._refresh()

    def set_armed(self, on: bool):
        self._armed = on
        self._refresh()

    def set_selected(self, on: bool):
        self._selected = on
        self._refresh()

    # ---------- events ----------

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
        self.signals.pressed.emit(self.out_id)
        e.accept()

    def mouseReleaseEvent(self, e):
        self._mouse = False
        self._refresh()
        self.signals.released.emit(self.out_id)
        e.accept()


class OutputView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QBrush(BG))
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.signals = CellSignals()
        self.cells: dict[str, OutputCellItem] = {}

        for out_id in OUTPUT_IDS:
            n = int(out_id.split("-")[1])
            cell = OutputCellItem(out_id, n, self.signals)
            col, row_top = mpc_position(out_id)
            cell.setPos(col * (CELL_SIZE + CELL_GAP), row_top * (CELL_SIZE + CELL_GAP))
            self._scene.addItem(cell)
            self.cells[out_id] = cell

        margin = 16.0
        w = GRID_COLS * CELL_SIZE + (GRID_COLS - 1) * CELL_GAP
        h = GRID_ROWS * CELL_SIZE + (GRID_ROWS - 1) * CELL_GAP
        scene_h = h + 2 * margin
        scene_w = scene_h * (VIEW_W / VIEW_H)
        x_offset = -(scene_w - (w + 2 * margin)) / 2 - margin
        self._scene.setSceneRect(x_offset, -margin, scene_w, scene_h)

    def fit(self):
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, e):
        self.fit()
        super().resizeEvent(e)

    def showEvent(self, e):
        self.fit()
        super().showEvent(e)
