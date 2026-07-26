from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPen
from PySide6.QtWidgets import (
    QGraphicsItemGroup,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
)


class LadderScene(QGraphicsScene):
    """Structured rail/wire/instruction rendering; execution remains in rsmcore."""

    def load_routine(self, routine):
        self.clear()
        left, right = 70, 1000
        spacing = 125
        height = max(150, len(routine.rungs) * spacing + 60)
        self.setSceneRect(0, 0, 1050, height)
        rail_pen = QPen(QColor("#1e293b"), 3)
        wire_pen = QPen(QColor("#475569"), 2)
        self.addLine(left, 20, left, height - 25, rail_pen)
        self.addLine(right, 20, right, height - 25, rail_pen)
        for number, rung in enumerate(routine.rungs, 1):
            y = 85 + (number - 1) * spacing
            number_item = self.addSimpleText(str(number))
            number_item.setBrush(QBrush(QColor("#64748b")))
            number_item.setPos(24, y - 10)
            comment = self.addSimpleText(rung.comment or f"Rung {number}")
            comment.setBrush(QBrush(QColor("#334155")))
            comment.setFont(QFont("Sans Serif", 9, QFont.Weight.DemiBold))
            comment.setPos(84, y - 47)
            x = 95
            self.addLine(left, y, x, y, wire_pen)
            for node in rung.nodes:
                group = QGraphicsItemGroup()
                box = QGraphicsRectItem(QRectF(x, y - 20, 120, 42))
                box.setPen(QPen(QColor("#475569"), 1.5))
                box.setBrush(QBrush(QColor("#f8fafc")))
                group.addToGroup(box)
                mnemonic = getattr(node, "mnemonic", node.__class__.__name__.upper())
                label = QGraphicsSimpleTextItem(mnemonic)
                label.setBrush(QBrush(QColor("#0f172a")))
                label.setFont(QFont("Monospace", 10, QFont.Weight.DemiBold))
                label.setPos(x + 10, y - 13)
                group.addToGroup(label)
                self.addItem(group)
                self.addLine(x + 120, y, x + 145, y, wire_pen)
                x += 145
            self.addLine(x, y, right, y, wire_pen)
