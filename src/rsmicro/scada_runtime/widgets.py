from collections import deque
from typing import Deque

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QDoubleSpinBox, QLabel, QProgressBar, QPushButton, QWidget


CARD_STYLE = """
QLabel {
  color: #e2e8f0;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 9px 14px;
  font-size: 16px;
}
"""
VALUE_STYLE = """
QLabel {
  color: #7dd3fc;
  background: #172033;
  border: 1px solid #0ea5e9;
  border-radius: 8px;
  padding: 9px 14px;
  font-size: 17px;
  font-weight: 600;
}
"""


class LiveLabel(QLabel):
    def update_value(self, value, quality="GOOD", forced=False):
        suffix = "" if quality == "GOOD" else f" [{quality}]"
        if forced:
            suffix += " [FORCED]"
        self.setText(f"{value}{suffix}")
        self.setAccessibleName(
            f"value {value}, quality {quality}" + (" forced" if forced else "")
        )


class BooleanIndicator(LiveLabel):
    def update_value(self, value, quality="GOOD", forced=False):
        super().update_value("Running" if value else "Stopped", quality, forced)


class OperatorButton(QPushButton):
    writeRequested = Signal(object)

    def __init__(self, text, action, parent=None):
        super().__init__(text, parent)
        self.action = action
        self.pressed.connect(self._press)
        self.released.connect(self._release)

    def _press(self):
        self.setText(self.text() + " (pending)")
        self.writeRequested.emit(self.action.get("value", True))

    def _release(self):
        if self.action.get("type") == "MOMENTARY":
            self.writeRequested.emit(self.action.get("release_value", False))


class NumericInput(QDoubleSpinBox):
    writeRequested = Signal(object)

    def commit(self):
        self.writeRequested.emit(self.value())


class TrendWidget(QWidget):
    def __init__(self, parent=None, maximum_points=1000):
        super().__init__(parent)
        self.points: Deque[tuple[object, float, str, bool]] = deque(maxlen=maximum_points)

    def add_point(self, timestamp, value, quality="GOOD", forced=False):
        self.points.append((timestamp, float(value), quality, forced))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(Qt.GlobalColor.lightGray)
        painter.drawText(12, 22, "Trend — waiting for live samples")
        good = [point for point in self.points if point[2] == "GOOD"]
        if len(good) > 1:
            values = [point[1] for point in good]
            low, high = min(values), max(values)
            span = high - low or 1
            for index in range(1, len(good)):
                x1 = (index - 1) * self.width() / (len(good) - 1)
                x2 = index * self.width() / (len(good) - 1)
                y1 = self.height() - (good[index - 1][1] - low) / span * (self.height() - 25)
                y2 = self.height() - (good[index][1] - low) / span * (self.height() - 25)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))


def _styled_label(text: str, style: str = CARD_STYLE) -> QLabel:
    label = QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
    label.setStyleSheet(style)
    return label


def create_widget(obj):
    widget_type = obj.type
    properties = obj.properties
    role = obj.style.get("role")
    if widget_type == "label":
        label = _styled_label(properties.get("text", "Label"))
        if role == "title":
            label.setStyleSheet(
                "color:#f8fafc;background:transparent;font-size:28px;font-weight:700;"
            )
        elif role == "note":
            label.setWordWrap(True)
        return label
    if widget_type == "boolean_indicator":
        return _styled_label(properties.get("placeholder", "OFF • STALE"), VALUE_STYLE)
    if widget_type in {"numeric_display", "connection_indicator", "force_indicator"}:
        return _styled_label(properties.get("placeholder", "—  STALE"), VALUE_STYLE)
    if widget_type == "alarm_banner":
        return _styled_label(
            properties.get("placeholder", "No live alarms"),
            "QLabel{color:#fbbf24;background:#422006;border:1px solid #d97706;"
            "border-radius:8px;padding:14px;font-size:17px;font-weight:600;}",
        )
    if widget_type in {"pushbutton", "navigation_button"}:
        return OperatorButton(properties.get("text", "Command"), obj.action)
    if widget_type == "numeric_input":
        return NumericInput()
    if widget_type == "bar":
        return QProgressBar()
    if widget_type == "trend":
        return TrendWidget(maximum_points=int(properties.get("maximum_points", 1000)))
    return _styled_label(widget_type.replace("_", " ").title() + " — unavailable")
