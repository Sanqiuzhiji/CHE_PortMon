# -*- coding: utf-8 -*-
import math
import uuid
from dataclasses import dataclass

from PyQt5.QtCore import QPoint, QPointF, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSlider,
    QSpinBox,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from models.channel_model import DEFAULT_CHANNEL_COLORS


@dataclass
class PlotCommand:
    payload: bytes
    repeat_count: int = 1


def _new_id():
    return uuid.uuid4().hex


def _crc8(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def _crc16_xmodem(data):
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def _checksum_bytes(data, checksum):
    if checksum == "sum8":
        return bytes([sum(data) & 0xFF])
    if checksum == "crc8":
        return bytes([_crc8(data)])
    if checksum == "crc16-xmodem":
        return _crc16_xmodem(data).to_bytes(2, "big")
    return b""


def _line_ending_bytes(line_ending):
    return {"none": b"", "LF": b"\n", "CRLF": b"\r\n"}.get(line_ending, b"\n")


def _build_plot_command(command_text, line_ending, repeat_count=1, checksum="none"):
    body = command_text.encode("utf-8")
    payload = body + _checksum_bytes(body, checksum) + _line_ending_bytes(line_ending)
    return PlotCommand(payload=payload, repeat_count=max(1, int(repeat_count)))


class _DragHandle(QLabel):
    def __init__(self, owner, text="", parent=None):
        super().__init__(text, parent)
        self.owner = owner
        self.setCursor(Qt.SizeAllCursor)
        self.setAlignment(Qt.AlignCenter)

    def mousePressEvent(self, event):
        self.owner._begin_drag(event)

    def mouseMoveEvent(self, event):
        self.owner._drag_move(event)

    def mouseReleaseEvent(self, event):
        self.owner._end_drag(event)


class _ResizeHandle(QLabel):
    def __init__(self, owner, parent=None):
        super().__init__("◢", parent)
        self.owner = owner
        self.setObjectName("plotControlResizeHandle")
        self.setCursor(Qt.SizeFDiagCursor)
        self.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.setFixedSize(16, 16)

    def mousePressEvent(self, event):
        self.owner._begin_resize(event)

    def mouseMoveEvent(self, event):
        self.owner._resize_move(event)

    def mouseReleaseEvent(self, event):
        self.owner._end_resize(event)


class BasePlotControl(QFrame):
    config_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)
    command_generated = pyqtSignal(object)

    def __init__(self, title="Control", control_id=None, parent=None):
        super().__init__(parent)
        self.control_id = control_id or _new_id()
        self.control_type = "base"
        self.title = title
        self._dragging = False
        self._drag_offset = QPoint()
        self._resizing = False
        self._resize_press_pos = QPoint()
        self._resize_start_size = QSize()
        self.setObjectName("plotControl")
        self.setProperty("selected", False)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setFocusPolicy(Qt.StrongFocus)

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(8, 8, 8, 8)
        self._root.setSpacing(6)
        self.header = _DragHandle(self, self.title, self)
        self.header.setObjectName("plotControlHeader")
        self._root.addWidget(self.header)
        self.body = QWidget(self)
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(6)
        self._root.addWidget(self.body)
        resize_row = QHBoxLayout()
        resize_row.setContentsMargins(0, 0, 0, 0)
        resize_row.addStretch(1)
        self.resize_handle = _ResizeHandle(self, self)
        resize_row.addWidget(self.resize_handle)
        self._root.addLayout(resize_row)
        self._apply_default_size()

    def _apply_default_size(self):
        self.resize(180, 120)

    def _begin_drag(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._dragging = False
        self._drag_offset = event.globalPos() - self.mapToGlobal(QPoint(0, 0))
        if hasattr(self.parentWidget(), "select_control"):
            self.parentWidget().select_control(self)

    def _drag_move(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self._dragging:
            self._dragging = True
        canvas = self.parentWidget()
        if canvas is None:
            return
        new_pos = canvas.mapFromGlobal(event.globalPos() - self._drag_offset)
        if hasattr(canvas, "adjust_control_position"):
            new_pos = canvas.adjust_control_position(self, new_pos)
        self.move(new_pos)

    def _end_drag(self, event):
        self._dragging = False
        if hasattr(self.parentWidget(), "select_control"):
            self.parentWidget().select_control(self)

    def _begin_resize(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._resizing = True
        self._resize_press_pos = event.globalPos()
        self._resize_start_size = self.size()
        if hasattr(self.parentWidget(), "select_control"):
            self.parentWidget().select_control(self)

    def _resize_move(self, event):
        if not self._resizing or not (event.buttons() & Qt.LeftButton):
            return
        delta = event.globalPos() - self._resize_press_pos
        new_size = QSize(
            self._resize_start_size.width() + delta.x(),
            self._resize_start_size.height() + delta.y(),
        )
        canvas = self.parentWidget()
        if hasattr(canvas, "adjust_control_size"):
            new_size = canvas.adjust_control_size(self, new_size)
        self.resize(new_size)

    def _end_resize(self, event):
        self._resizing = False
        if hasattr(self.parentWidget(), "select_control"):
            self.parentWidget().select_control(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.childAt(event.pos()) is None:
            self._begin_drag(event)
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self._drag_move(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._end_drag(event)
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        self._show_context_menu(event.globalPos())

    def _show_context_menu(self, global_pos):
        menu = QMenu(self)
        config_action = menu.addAction("Config")
        delete_action = menu.addAction("Delete")
        action = menu.exec_(global_pos)
        if action == config_action:
            self.config_requested.emit(self)
        elif action == delete_action:
            self.delete_requested.emit(self)

    def set_selected(self, selected):
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def to_dict(self):
        config = self.control_config()
        return {
            "id": self.control_id,
            "type": self.control_type,
            "x": self.x(),
            "y": self.y(),
            "w": self.width(),
            "h": self.height(),
            "config": config,
        }

    def control_config(self):
        return {}

    def apply_config(self, config):
        return None


class TogglePlotControl(BasePlotControl):
    def __init__(self, control_id=None, parent=None):
        super().__init__("Toggle", control_id=control_id, parent=parent)
        self.control_type = "toggle"
        self._on_command = "ON"
        self._off_command = "OFF"
        self._line_ending = "LF"
        self._repeat_count = 1
        self._is_on = False

        self.state_button = QPushButton("OFF", self.body)
        self.state_button.setCheckable(True)
        self.state_button.clicked.connect(self._handle_toggle)
        self.body_layout.addWidget(self.state_button)
        self.preview_label = QLabel("Toggle", self.body)
        self.preview_label.setObjectName("plotControlPreviewLabel")
        self.body_layout.addWidget(self.preview_label)
        self._apply_default_size()
        self._refresh_view()

    def _apply_default_size(self):
        self.resize(160, 110)

    def _handle_toggle(self, checked):
        self._is_on = checked
        self._refresh_view()
        self.command_generated.emit(self._build_command())

    def _build_command(self):
        command = self._on_command if self._is_on else self._off_command
        return _build_plot_command(command, self._line_ending, self._repeat_count)

    def _refresh_view(self):
        self.state_button.setText("ON" if self._is_on else "OFF")
        self.preview_label.setText(self.title)

    def control_config(self):
        return {
            "title": self.title,
            "on_command": self._on_command,
            "off_command": self._off_command,
            "line_ending": self._line_ending,
            "repeat_count": self._repeat_count,
        }

    def apply_config(self, config):
        self.title = config.get("title", self.title)
        self._on_command = config.get("on_command", self._on_command)
        self._off_command = config.get("off_command", self._off_command)
        self._line_ending = config.get("line_ending", self._line_ending)
        self._repeat_count = int(config.get("repeat_count", self._repeat_count))
        self.header.setText(self.title)
        self._refresh_view()


class SliderPlotControl(BasePlotControl):
    def __init__(self, control_id=None, parent=None):
        super().__init__("Serial Cmd", control_id=control_id, parent=parent)
        self.control_type = "slider"
        self._command_name = "Serial Cmd"
        self._min_value = -100.0
        self._max_value = 100.0
        self._step = 1.0
        self._repeat_count = 1
        self._checksum = "none"
        self._joiner = ":"
        self._format = "%.3f"
        self._line_ending = "LF"
        self._ascii_mode = False
        self._value = 0.0

        self.value_label = QLabel("0.000", self.body)
        self.value_label.setObjectName("plotControlValueLabel")
        self.value_slider = QSlider(Qt.Horizontal, self.body)
        self.value_slider.setRange(0, 1000)
        self.value_slider.valueChanged.connect(self._handle_slider_changed)
        self.value_spin = QDoubleSpinBox(self.body)
        self.value_spin.setRange(self._min_value, self._max_value)
        self.value_spin.setSingleStep(self._step)
        self.value_spin.setValue(self._value)
        self.value_spin.valueChanged.connect(self._handle_spin_changed)
        self.body_layout.addWidget(self.value_label)
        self.body_layout.addWidget(self.value_slider)
        row = QHBoxLayout()
        row.addWidget(QLabel("Serial Cmd", self.body))
        row.addWidget(self.value_spin)
        self.body_layout.addLayout(row)
        self._apply_default_size()
        self._refresh_view()

    def _apply_default_size(self):
        self.resize(240, 130)

    def _handle_slider_changed(self, value):
        ratio = value / 1000.0
        self._value = self._min_value + (self._max_value - self._min_value) * ratio
        self.value_spin.blockSignals(True)
        self.value_spin.setValue(self._value)
        self.value_spin.blockSignals(False)
        self._refresh_view()
        self.command_generated.emit(self._build_command())

    def _handle_spin_changed(self, value):
        self._value = float(value)
        ratio = 0 if self._max_value == self._min_value else (self._value - self._min_value) / (self._max_value - self._min_value)
        self.value_slider.blockSignals(True)
        self.value_slider.setValue(int(max(0, min(1, ratio)) * 1000))
        self.value_slider.blockSignals(False)
        self._refresh_view()
        self.command_generated.emit(self._build_command())

    def _build_command(self):
        command = f"{self._command_name}{self._joiner}{self._format_value(self._value)}"
        return _build_plot_command(command, self._line_ending, self._repeat_count, self._checksum)

    def _format_value(self, value):
        try:
            return self._format % value
        except Exception:
            return f"{value:.3f}"

    def _refresh_view(self):
        self.value_label.setText(self._format_value(self._value))
        self.header.setText(self._command_name)

    def control_config(self):
        return {
            "command_name": self._command_name,
            "min_value": self._min_value,
            "max_value": self._max_value,
            "step": self._step,
            "repeat_count": self._repeat_count,
            "checksum": self._checksum,
            "joiner": self._joiner,
            "format": self._format,
            "line_ending": self._line_ending,
            "ascii_mode": self._ascii_mode,
        }

    def apply_config(self, config):
        self._command_name = config.get("command_name", self._command_name)
        self._min_value = float(config.get("min_value", self._min_value))
        self._max_value = float(config.get("max_value", self._max_value))
        self._step = float(config.get("step", self._step))
        self._repeat_count = int(config.get("repeat_count", self._repeat_count))
        self._checksum = config.get("checksum", self._checksum)
        self._joiner = config.get("joiner", self._joiner)
        self._format = config.get("format", self._format)
        self._line_ending = config.get("line_ending", self._line_ending)
        self._ascii_mode = bool(config.get("ascii_mode", self._ascii_mode))
        self.header.setText(self._command_name)
        self.value_spin.setRange(self._min_value, self._max_value)
        self.value_spin.setSingleStep(self._step)
        self._refresh_view()


class ModePlotControl(BasePlotControl):
    def __init__(self, control_id=None, parent=None):
        super().__init__("Mode", control_id=control_id, parent=parent)
        self.control_type = "mode"
        self._command_name = "Mode"
        self._values = ["0", "1", "2", "3"]
        self._labels = ["idle", "ready", "run", "44"]
        self._repeat_count = 1
        self._checksum = "none"
        self._joiner = ":"
        self._line_ending = "LF"
        self._ascii_mode = False
        self._current_index = 0

        self.label_row = QHBoxLayout()
        self.body_layout.addLayout(self.label_row)
        self.buttons_row = QHBoxLayout()
        self.body_layout.addLayout(self.buttons_row)
        self._rebuild_buttons()
        self._apply_default_size()
        self._refresh_view()

    def _apply_default_size(self):
        self.resize(240, 130)

    def _rebuild_buttons(self):
        while self.label_row.count():
            item = self.label_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        while self.buttons_row.count():
            item = self.buttons_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for label in self._labels:
            self.label_row.addWidget(QLabel(label, self.body))
        self.label_row.addStretch(1)
        for index, label in enumerate(self._labels):
            button = QPushButton(label, self.body)
            button.setCheckable(True)
            button.setChecked(index == self._current_index)
            button.clicked.connect(lambda checked=False, idx=index: self._handle_mode_clicked(idx))
            self.buttons_row.addWidget(button)
        self.buttons_row.addStretch(1)

    def _handle_mode_clicked(self, index):
        self._current_index = index
        self._refresh_view()
        self.command_generated.emit(self._build_command())

    def _build_command(self):
        value = self._values[self._current_index] if self._values else "0"
        command = f"{self._command_name}{self._joiner}{value}"
        return _build_plot_command(command, self._line_ending, self._repeat_count, self._checksum)

    def _refresh_view(self):
        self.header.setText(self._command_name)

    def control_config(self):
        return {
            "command_name": self._command_name,
            "values": ";".join(self._values),
            "labels": ";".join(self._labels),
            "repeat_count": self._repeat_count,
            "checksum": self._checksum,
            "joiner": self._joiner,
            "line_ending": self._line_ending,
            "ascii_mode": self._ascii_mode,
        }

    def apply_config(self, config):
        self._command_name = config.get("command_name", self._command_name)
        self._values = [item.strip() for item in str(config.get("values", ";".join(self._values))).split(";") if item.strip()]
        self._labels = [item.strip() for item in str(config.get("labels", ";".join(self._labels))).split(";") if item.strip()]
        self._repeat_count = int(config.get("repeat_count", self._repeat_count))
        self._checksum = config.get("checksum", self._checksum)
        self._joiner = config.get("joiner", self._joiner)
        self._line_ending = config.get("line_ending", self._line_ending)
        self._ascii_mode = bool(config.get("ascii_mode", self._ascii_mode))
        self.header.setText(self._command_name)
        self._rebuild_buttons()


class GaugePlotControl(BasePlotControl):
    def __init__(self, channel_manager=None, control_id=None, parent=None):
        super().__init__("Gauge", control_id=control_id, parent=parent)
        self.control_type = "gauge"
        self.channel_manager = channel_manager
        self._channel_key = "CH0"
        self._use_custom_name = False
        self._custom_name = "Gauge"
        self._min_value = -100.0
        self._max_value = 100.0
        self._precision = 1
        self._unit = ""
        self._current_value = 0.0
        self.value_label = QLabel("CH0: 0.0", self.body)
        self.value_label.setAlignment(Qt.AlignCenter)
        self.body_layout.addWidget(self.value_label)
        self._apply_default_size()
        if self.channel_manager is not None:
            self.channel_manager.channels_changed.connect(self._handle_channels_changed)
        self._refresh_view()

    def _apply_default_size(self):
        self.resize(200, 180)

    def _handle_channels_changed(self, channels):
        channel = None
        for item in channels:
            if item.key == self._channel_key:
                channel = item
                break
        if channel is not None:
            self._current_value = channel.display_value if channel.enabled else 0.0
            if not self._use_custom_name:
                self.title = channel.name
                self.header.setText(self.title)
        self._refresh_view()

    def _refresh_view(self):
        label = self._custom_name if self._use_custom_name else self._channel_key
        self.value_label.setText(f"{label}: {self._current_value:.{self._precision}f}{self._unit}")
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(18, 34, -18, -18)
        painter.setPen(QPen(QColor("#455468"), 8))
        painter.drawArc(rect, 210 * 16, -240 * 16)
        ratio = 0 if self._max_value == self._min_value else (self._current_value - self._min_value) / (self._max_value - self._min_value)
        ratio = max(0.0, min(1.0, ratio))
        painter.setPen(QPen(QColor("#2d8cff"), 8))
        painter.drawArc(rect, 210 * 16, int(-240 * 16 * ratio))

    def control_config(self):
        return {
            "channel_key": self._channel_key,
            "use_custom_name": self._use_custom_name,
            "custom_name": self._custom_name,
            "min_value": self._min_value,
            "max_value": self._max_value,
            "precision": self._precision,
            "unit": self._unit,
        }

    def apply_config(self, config):
        self._channel_key = config.get("channel_key", self._channel_key)
        self._use_custom_name = bool(config.get("use_custom_name", self._use_custom_name))
        self._custom_name = config.get("custom_name", self._custom_name)
        self._min_value = float(config.get("min_value", self._min_value))
        self._max_value = float(config.get("max_value", self._max_value))
        self._precision = int(config.get("precision", self._precision))
        self._unit = config.get("unit", self._unit)
        self._refresh_view()


CONTROL_TYPES = {
    "toggle": TogglePlotControl,
    "slider": SliderPlotControl,
    "mode": ModePlotControl,
    "gauge": GaugePlotControl,
}


def create_plot_control(control_type, channel_manager=None, control_id=None, parent=None):
    control_cls = CONTROL_TYPES.get(control_type)
    if control_cls is None:
        raise ValueError(f"Unknown plot control type: {control_type}")
    if control_type == "gauge":
        return control_cls(channel_manager=channel_manager, control_id=control_id, parent=parent)
    return control_cls(control_id=control_id, parent=parent)


class PlotCanvas(QWidget):
    command_generated = pyqtSignal(object)

    def __init__(self, channel_manager=None, parent=None):
        super().__init__(parent)
        self.setObjectName("plotCanvas")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.channel_manager = channel_manager
        self._controls = []
        self._selected_control = None
        self._grid_enabled = True
        self._grid_size = 20
        self._snap_to_grid = True
        self._command_signal_bound = False
        self._selected_pen = QPen(QColor("#2d8cff"), 2)

    def grid_size(self):
        return self._grid_size

    def set_grid_size(self, size):
        self._grid_size = max(5, min(100, int(size)))
        self.update()

    def snap_to_grid(self):
        return self._snap_to_grid

    def set_snap_to_grid(self, enabled):
        self._snap_to_grid = bool(enabled)

    def adjust_control_position(self, control, pos):
        x = max(0, min(pos.x(), max(0, self.width() - control.width())))
        y = max(0, min(pos.y(), max(0, self.height() - control.height())))
        if self._snap_to_grid:
            grid = self._grid_size
            x = round(x / grid) * grid
            y = round(y / grid) * grid
        return QPoint(x, y)

    def adjust_control_size(self, control, size):
        min_size = control.minimumSizeHint()
        width = max(80, min_size.width(), size.width())
        height = max(70, min_size.height(), size.height())
        if self._snap_to_grid:
            grid = self._grid_size
            width = max(grid, round(width / grid) * grid)
            height = max(grid, round(height / grid) * grid)
        width = min(width, max(80, self.width() - control.x()))
        height = min(height, max(70, self.height() - control.y()))
        return QSize(width, height)

    def add_control(self, control_type, pos=None, config=None, control_id=None):
        control = create_plot_control(control_type, channel_manager=self.channel_manager, control_id=control_id, parent=self)
        control.config_requested.connect(self._edit_control)
        control.delete_requested.connect(self.remove_control)
        control.command_generated.connect(self._forward_command)
        if config:
            control.apply_config(config)
        if pos is None:
            pos = QPoint(40 + 24 * len(self._controls), 40 + 20 * len(self._controls))
        pos = self.adjust_control_position(control, pos)
        control.move(pos)
        control.show()
        self._controls.append(control)
        self.select_control(control)
        return control

    def remove_control(self, control):
        if control in self._controls:
            self._controls.remove(control)
        if self._selected_control is control:
            self._selected_control = None
        control.deleteLater()
        self.update()

    def _forward_command(self, command):
        self.command_generated.emit(command)

    def clear_controls(self):
        for control in list(self._controls):
            control.deleteLater()
        self._controls.clear()
        self._selected_control = None
        self.update()

    def controls(self):
        return list(self._controls)

    def select_control(self, control):
        if self._selected_control is control:
            return
        if self._selected_control is not None:
            self._selected_control.set_selected(False)
        self._selected_control = control
        if self._selected_control is not None:
            self._selected_control.set_selected(True)
            self._selected_control.raise_()
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete and self._selected_control is not None:
            self.remove_control(self._selected_control)
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.select_control(None)
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        self._show_context_menu(event.globalPos())

    def _show_context_menu(self, global_pos):
        menu = QMenu(self)
        add_plot = menu.addAction("Add Plot Control")
        add_plot.setEnabled(False)
        add_slider = menu.addAction("Add Slider Control")
        add_toggle = menu.addAction("Add Toggle Control")
        add_mode = menu.addAction("Add Mode Control")
        add_gauge = menu.addAction("Add Gauge Control")
        add_pose = menu.addAction("Add Pose Control")
        add_pose.setEnabled(False)
        action = menu.exec_(global_pos)
        if action is None:
            return
        local_pos = self.mapFromGlobal(global_pos)
        if action == add_slider:
            self.add_control("slider", local_pos)
        elif action == add_toggle:
            self.add_control("toggle", local_pos)
        elif action == add_mode:
            self.add_control("mode", local_pos)
        elif action == add_gauge:
            self.add_control("gauge", local_pos)

    def _edit_control(self, control):
        if isinstance(control, TogglePlotControl):
            dialog = _ToggleConfigDialog(control, self)
        elif isinstance(control, SliderPlotControl):
            dialog = _SliderConfigDialog(control, self)
        elif isinstance(control, ModePlotControl):
            dialog = _ModeConfigDialog(control, self)
        elif isinstance(control, GaugePlotControl):
            dialog = _GaugeConfigDialog(control, self)
        else:
            return
        if dialog.exec_() == QDialog.Accepted:
            control.apply_config(dialog.result_config())
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#242424"))
        self._paint_grid(painter)
        if not self._controls:
            painter.setPen(QColor("#8f9aa6"))
            painter.drawText(self.rect(), Qt.AlignCenter, "当前工作区为空\n右键空白区域可添加绘图、滑条、开关等控件\n选中控件后可删除，拖动可调整布局")

    def _paint_grid(self, painter):
        w = self.width()
        h = self.height()
        minor = QColor("#2f2f2f")
        major = QColor("#3a3a3a")
        grid = self._grid_size
        major_step = grid * 4
        for x in range(0, w, grid):
            painter.setPen(QPen(major if x % major_step == 0 else minor, 1))
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, grid):
            painter.setPen(QPen(major if y % major_step == 0 else minor, 1))
            painter.drawLine(0, y, w, y)


class _BaseConfigDialog(QDialog):
    def __init__(self, control, parent=None):
        super().__init__(parent)
        self.control = control
        self._result = {}
        self.setWindowTitle("Control Config")
        self.resize(360, 240)
        self.layout = QVBoxLayout(self)
        self.form = QFormLayout()
        self.layout.addLayout(self.form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)

    def result_config(self):
        return self._result


class _ToggleConfigDialog(_BaseConfigDialog):
    def __init__(self, control, parent=None):
        super().__init__(control, parent)
        config = control.control_config()
        self.title_edit = QLineEdit(config["title"], self)
        self.on_edit = QLineEdit(config["on_command"], self)
        self.off_edit = QLineEdit(config["off_command"], self)
        self.line_combo = QComboBox(self)
        self.line_combo.addItems(["none", "LF", "CRLF"])
        self.line_combo.setCurrentText(config["line_ending"])
        self.repeat_spin = QSpinBox(self)
        self.repeat_spin.setRange(1, 1000)
        self.repeat_spin.setValue(config["repeat_count"])
        self.form.addRow("Control Name", self.title_edit)
        self.form.addRow("ON Command", self.on_edit)
        self.form.addRow("OFF Command", self.off_edit)
        self.form.addRow("Line Ending", self.line_combo)
        self.form.addRow("Repeat", self.repeat_spin)

    def accept(self):
        self._result = {
            "title": self.title_edit.text().strip() or "Toggle",
            "on_command": self.on_edit.text().strip() or "ON",
            "off_command": self.off_edit.text().strip() or "OFF",
            "line_ending": self.line_combo.currentText(),
            "repeat_count": self.repeat_spin.value(),
        }
        super().accept()


class _SliderConfigDialog(_BaseConfigDialog):
    def __init__(self, control, parent=None):
        super().__init__(control, parent)
        config = control.control_config()
        self.command_edit = QLineEdit(config["command_name"], self)
        self.min_spin = QDoubleSpinBox(self)
        self.min_spin.setRange(-1e9, 1e9)
        self.min_spin.setValue(config["min_value"])
        self.max_spin = QDoubleSpinBox(self)
        self.max_spin.setRange(-1e9, 1e9)
        self.max_spin.setValue(config["max_value"])
        self.step_spin = QDoubleSpinBox(self)
        self.step_spin.setRange(0.0001, 1e9)
        self.step_spin.setValue(config["step"])
        self.repeat_spin = QSpinBox(self)
        self.repeat_spin.setRange(1, 1000)
        self.repeat_spin.setValue(config["repeat_count"])
        self.checksum_combo = QComboBox(self)
        self.checksum_combo.addItems(["none", "sum8", "crc8", "crc16-xmodem"])
        self.checksum_combo.setCurrentText(config["checksum"])
        self.joiner_edit = QLineEdit(config["joiner"], self)
        self.format_edit = QLineEdit(config["format"], self)
        self.line_combo = QComboBox(self)
        self.line_combo.addItems(["none", "LF", "CRLF"])
        self.line_combo.setCurrentText(config["line_ending"])
        self.ascii_check = QCheckBox(self)
        self.ascii_check.setChecked(config["ascii_mode"])
        self.form.addRow("Command Name", self.command_edit)
        self.form.addRow("Min Value", self.min_spin)
        self.form.addRow("Max Value", self.max_spin)
        self.form.addRow("Step", self.step_spin)
        self.form.addRow("Repeat", self.repeat_spin)
        self.form.addRow("Checksum", self.checksum_combo)
        self.form.addRow("Joiner", self.joiner_edit)
        self.form.addRow("Format", self.format_edit)
        self.form.addRow("Line Ending", self.line_combo)
        self.form.addRow("ASCII Mode", self.ascii_check)

    def accept(self):
        self._result = {
            "command_name": self.command_edit.text().strip() or "Serial Cmd",
            "min_value": self.min_spin.value(),
            "max_value": self.max_spin.value(),
            "step": self.step_spin.value(),
            "repeat_count": self.repeat_spin.value(),
            "checksum": self.checksum_combo.currentText(),
            "joiner": self.joiner_edit.text() or ":",
            "format": self.format_edit.text() or "%.3f",
            "line_ending": self.line_combo.currentText(),
            "ascii_mode": self.ascii_check.isChecked(),
        }
        super().accept()


class _ModeConfigDialog(_BaseConfigDialog):
    def __init__(self, control, parent=None):
        super().__init__(control, parent)
        config = control.control_config()
        self.command_edit = QLineEdit(config["command_name"], self)
        self.values_edit = QLineEdit(config["values"], self)
        self.labels_edit = QLineEdit(config["labels"], self)
        self.repeat_spin = QSpinBox(self)
        self.repeat_spin.setRange(1, 1000)
        self.repeat_spin.setValue(config["repeat_count"])
        self.checksum_combo = QComboBox(self)
        self.checksum_combo.addItems(["none", "sum8", "crc8", "crc16-xmodem"])
        self.checksum_combo.setCurrentText(config["checksum"])
        self.joiner_edit = QLineEdit(config["joiner"], self)
        self.line_combo = QComboBox(self)
        self.line_combo.addItems(["none", "LF", "CRLF"])
        self.line_combo.setCurrentText(config["line_ending"])
        self.ascii_check = QCheckBox(self)
        self.ascii_check.setChecked(config["ascii_mode"])
        self.form.addRow("Command Name", self.command_edit)
        self.form.addRow("Mode Values", self.values_edit)
        self.form.addRow("Mode Labels", self.labels_edit)
        self.form.addRow("Repeat", self.repeat_spin)
        self.form.addRow("Checksum", self.checksum_combo)
        self.form.addRow("Joiner", self.joiner_edit)
        self.form.addRow("Line Ending", self.line_combo)
        self.form.addRow("ASCII Mode", self.ascii_check)

    def accept(self):
        self._result = {
            "command_name": self.command_edit.text().strip() or "Mode",
            "values": self.values_edit.text().strip() or "0;1;2;3",
            "labels": self.labels_edit.text().strip() or "idle;ready;run;44",
            "repeat_count": self.repeat_spin.value(),
            "checksum": self.checksum_combo.currentText(),
            "joiner": self.joiner_edit.text() or ":",
            "line_ending": self.line_combo.currentText(),
            "ascii_mode": self.ascii_check.isChecked(),
        }
        super().accept()


class _GaugeConfigDialog(_BaseConfigDialog):
    def __init__(self, control, parent=None):
        super().__init__(control, parent)
        config = control.control_config()
        self.channel_combo = QComboBox(self)
        for key in ["CH0", "CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7", "CH8", "CH9"]:
            self.channel_combo.addItem(key)
        self.channel_combo.setCurrentText(config["channel_key"])
        self.use_custom_check = QCheckBox(self)
        self.use_custom_check.setChecked(config["use_custom_name"])
        self.custom_name_edit = QLineEdit(config["custom_name"], self)
        self.min_spin = QDoubleSpinBox(self)
        self.min_spin.setRange(-1e9, 1e9)
        self.min_spin.setValue(config["min_value"])
        self.max_spin = QDoubleSpinBox(self)
        self.max_spin.setRange(-1e9, 1e9)
        self.max_spin.setValue(config["max_value"])
        self.precision_spin = QSpinBox(self)
        self.precision_spin.setRange(0, 6)
        self.precision_spin.setValue(config["precision"])
        self.unit_edit = QLineEdit(config["unit"], self)
        self.form.addRow("Channel", self.channel_combo)
        self.form.addRow("Use Custom Name", self.use_custom_check)
        self.form.addRow("Custom Name", self.custom_name_edit)
        self.form.addRow("Min Value", self.min_spin)
        self.form.addRow("Max Value", self.max_spin)
        self.form.addRow("Precision", self.precision_spin)
        self.form.addRow("Unit", self.unit_edit)

    def accept(self):
        self._result = {
            "channel_key": self.channel_combo.currentText(),
            "use_custom_name": self.use_custom_check.isChecked(),
            "custom_name": self.custom_name_edit.text().strip() or "Gauge",
            "min_value": self.min_spin.value(),
            "max_value": self.max_spin.value(),
            "precision": self.precision_spin.value(),
            "unit": self.unit_edit.text(),
        }
        super().accept()
