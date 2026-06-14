# -*- coding: utf-8 -*-
import csv
import math
import time
from collections import deque
from pathlib import Path

from PyQt5.QtCore import QPoint, QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from models.channel_model import DEFAULT_CHANNEL_COLORS


DRAW_MODES = {
    "line": "线图",
    "points": "点图",
    "line_points": "点线图",
}

TRACER_STYLES = {
    "cross_horizontal": "十字形 + 水平",
    "circle_slash": "圆圈 + 斜线",
    "diamond_slash": "菱形 + 斜线",
}

X_UNITS = {
    "s": ("秒 (s)", 1.0),
    "ms": ("毫秒 (ms)", 1000.0),
    "us": ("微秒 (us)", 1000000.0),
}

WHEEL_SPEEDS = {
    0.10: "慢速 (10%)",
    0.20: "中速 (20%)",
    0.35: "快速 (35%)",
}

CURSOR_VALUE_MODES = {
    "linear": "线性插值",
    "nearest": "最近点",
}


class PlotDataBuffer:
    def __init__(self, max_points=20000):
        self._max_points = int(max_points)
        self._frames = deque(maxlen=self._max_points)

    def set_max_points(self, max_points):
        max_points = max(100, int(max_points))
        if max_points == self._max_points:
            return
        self._max_points = max_points
        self._frames = deque(list(self._frames)[-self._max_points :], maxlen=self._max_points)

    def max_points(self):
        return self._max_points

    def clear(self):
        self._frames.clear()

    def append(self, timestamp_s, values):
        self._frames.append((float(timestamp_s), dict(values or {})))

    def latest_time(self):
        if not self._frames:
            return 0.0
        return self._frames[-1][0]

    def total_frames(self):
        return len(self._frames)

    def channel_keys(self):
        keys = set()
        for _timestamp, values in self._frames:
            keys.update(values.keys())
        return sorted(keys, key=_channel_sort_key)

    def series(self, key, start_s=None, end_s=None):
        points = []
        for timestamp, values in self._frames:
            if start_s is not None and timestamp < start_s:
                continue
            if end_s is not None and timestamp > end_s:
                continue
            if key in values:
                points.append((timestamp, values[key]))
        return points

    def visible_point_count(self, keys, start_s=None, end_s=None):
        count = 0
        keys = set(keys)
        for timestamp, values in self._frames:
            if start_s is not None and timestamp < start_s:
                continue
            if end_s is not None and timestamp > end_s:
                continue
            count += sum(1 for key in keys if key in values)
        return count

    def y_range(self, keys, start_s=None, end_s=None):
        min_value = None
        max_value = None
        keys = set(keys)
        for timestamp, values in self._frames:
            if start_s is not None and timestamp < start_s:
                continue
            if end_s is not None and timestamp > end_s:
                continue
            for key in keys:
                if key not in values:
                    continue
                value = values[key]
                min_value = value if min_value is None else min(min_value, value)
                max_value = value if max_value is None else max(max_value, value)
        if min_value is None or max_value is None:
            return -1.0, 1.0
        if math.isclose(min_value, max_value):
            return min_value - 1.0, max_value + 1.0
        padding = (max_value - min_value) * 0.08
        return min_value - padding, max_value + padding

    def cursor_values(self, keys, cursor_s, mode="nearest"):
        result = {}
        for key in keys:
            points = self.series(key)
            if not points:
                continue
            if mode == "linear":
                result[key] = _linear_value(points, cursor_s)
            else:
                result[key] = min(points, key=lambda item: abs(item[0] - cursor_s))[1]
        return result

    def export_csv(self, path, channel_keys=None):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        keys = list(channel_keys or self.channel_keys())
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["time_s"] + keys)
            for timestamp, values in self._frames:
                writer.writerow([f"{timestamp:.9f}"] + [_format_csv_value(values.get(key)) for key in keys])


class PlotDrawArea(QWidget):
    context_menu_requested = pyqtSignal(QPoint)
    cursor_values_changed = pyqtSignal(dict)

    def __init__(self, plot_widget, parent=None):
        super().__init__(parent)
        self.plot_widget = plot_widget
        self.setObjectName("PlotDrawArea")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self._hover_pos = None
        self._hover_channel = None
        self._drag_mode = None
        self._last_mouse_pos = QPoint()
        self.live_tail_ratio = 0.78
        self.live_tail_dragging = False
        self._fps_times = deque(maxlen=80)
        self._last_y_range = (-1.0, 1.0)

    def reset_view_to_latest(self):
        self.update()

    def current_view_range(self):
        span = self.plot_widget.time_window_s()
        latest = self.plot_widget.buffer.latest_time()
        left_duration = span * self.live_tail_ratio
        right_duration = span * (1.0 - self.live_tail_ratio)
        return latest - left_duration, latest + right_duration

    def contextMenuEvent(self, event):
        self.context_menu_requested.emit(event.globalPos())
        event.accept()

    def wheelEvent(self, event):
        plot_rect = self._plot_rect()
        if event.pos().x() < plot_rect.left():
            self._zoom_y_axis(event.pos(), event.angleDelta().y() > 0)
            event.accept()
            return

        old_start, old_end = self.current_view_range()
        old_span = max(0.1, old_end - old_start)
        speed = self.plot_widget.wheel_speed()
        zoom_in = event.angleDelta().y() > 0
        new_span = old_span * (1.0 - speed if zoom_in else 1.0 + speed)
        new_span = max(0.1, min(120.0, new_span))
        self.plot_widget.set_time_window_s(new_span, reset_view=False)
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        self._last_mouse_pos = event.pos()
        if event.button() == Qt.LeftButton and self._is_near_live_tail(event.pos()):
            self.live_tail_dragging = True
            self._set_live_tail_from_x(event.pos().x())
            event.accept()
            return
        if event.button() in (Qt.LeftButton, Qt.MiddleButton):
            self.setFocus(Qt.MouseFocusReason)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self._set_hover_pos(event.pos())
        if self.live_tail_dragging:
            self._set_live_tail_from_x(event.pos().x())
            event.accept()
            return
        self.setCursor(Qt.SizeHorCursor if self._is_near_live_tail(event.pos()) else Qt.ArrowCursor)
        self._update_hover_channel(event.pos())
        event.accept()

    def mouseReleaseEvent(self, event):
        self.live_tail_dragging = False
        if event.button() in (Qt.LeftButton, Qt.MiddleButton):
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        self._hover_pos = None
        if not self.live_tail_dragging:
            self.setCursor(Qt.ArrowCursor)
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        now = time.perf_counter()
        self._fps_times.append(now)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#242424"))

        plot_rect = self._plot_rect()
        self._paint_plot_background(painter, plot_rect)

        visible_keys = self.plot_widget.visible_channel_keys()
        start_s, end_s = self.current_view_range()
        y_min, y_max = self.plot_widget.buffer.y_range(visible_keys, start_s, end_s)
        if not self.plot_widget.auto_range():
            y_min, y_max = self._last_y_range
        else:
            self._last_y_range = (y_min, y_max)

        self._paint_grid(painter, plot_rect, start_s, end_s, y_min, y_max)
        if not visible_keys or self.plot_widget.buffer.total_frames() == 0:
            painter.setPen(QColor("#8f9aa6"))
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无通道数据，请切换到 JustFloat 模式并接收数据")
        else:
            self._paint_series(painter, plot_rect, visible_keys, start_s, end_s, y_min, y_max)
            self._paint_channel_label(painter, plot_rect, visible_keys)
            self._paint_live_tail_cursor(painter, plot_rect)

        self._paint_hover_crosshair(painter, plot_rect, start_s, end_s, y_min, y_max)
        self._paint_status(painter, plot_rect, visible_keys, start_s, end_s)

    def _plot_rect(self):
        return self.rect().adjusted(58, 24, -18, -34)

    def _paint_plot_background(self, painter, plot_rect):
        painter.save()
        painter.setPen(QPen(QColor("#454545"), 1))
        painter.setBrush(QColor("#242424"))
        painter.drawRoundedRect(plot_rect.adjusted(-1, -1, 1, 1), 6, 6)
        painter.restore()

    def _paint_grid(self, painter, plot_rect, start_s, end_s, y_min, y_max):
        painter.save()
        minor_pen = QPen(QColor("#303030"), 1)
        major_pen = QPen(QColor("#3e3e3e"), 1)
        text_pen = QPen(QColor("#9ca3af"), 1)

        major_x = 5
        minor_x = major_x * 4
        for index in range(minor_x + 1):
            x = plot_rect.left() + plot_rect.width() * index / minor_x
            painter.setPen(major_pen if index % 4 == 0 else minor_pen)
            painter.drawLine(int(x), int(plot_rect.top()), int(x), int(plot_rect.bottom()))

        major_y = 6
        minor_y = major_y * 2
        for index in range(minor_y + 1):
            y = plot_rect.top() + plot_rect.height() * index / minor_y
            painter.setPen(major_pen if index % 2 == 0 else minor_pen)
            painter.drawLine(int(plot_rect.left()), int(y), int(plot_rect.right()), int(y))

        painter.setPen(text_pen)
        unit_scale = X_UNITS[self.plot_widget.x_unit()][1]
        for index in range(major_x + 1):
            ratio = index / major_x
            x = plot_rect.left() + plot_rect.width() * ratio
            value = (start_s + (end_s - start_s) * ratio) * unit_scale
            painter.drawText(int(x) - 30, int(plot_rect.bottom()) + 17, 60, 16, Qt.AlignCenter, _format_axis(value))

        for index in range(major_y + 1):
            ratio = index / major_y
            y = plot_rect.bottom() - plot_rect.height() * ratio
            value = y_min + (y_max - y_min) * ratio
            painter.drawText(2, int(y) - 8, 52, 16, Qt.AlignRight | Qt.AlignVCenter, _format_axis(value))

        painter.restore()

    def _paint_series(self, painter, plot_rect, visible_keys, start_s, end_s, y_min, y_max):
        painter.save()
        painter.setClipRect(plot_rect.adjusted(1, 1, -1, -1))
        draw_mode = self.plot_widget.draw_mode()
        for key in visible_keys:
            points = self.plot_widget.buffer.series(key, start_s, end_s)
            if not points:
                continue
            decimate_limit = max(20000, plot_rect.width() * 12) if draw_mode in ("line", "line_points") else max(200, plot_rect.width() * 2)
            points = _decimate_points(points, int(decimate_limit))
            color = QColor(self.plot_widget.channel_color(key))
            mapped = [self._map_point(timestamp, value, plot_rect, start_s, end_s, y_min, y_max) for timestamp, value in points]
            if draw_mode in ("line", "line_points") and len(mapped) >= 2:
                path = QPainterPath(mapped[0])
                for point in mapped[1:]:
                    path.lineTo(point)
                pen = QPen(color, 1.6)
                pen.setCapStyle(Qt.RoundCap)
                pen.setJoinStyle(Qt.RoundJoin)
                painter.setPen(pen)
                painter.drawPath(path)
            if draw_mode in ("points", "line_points"):
                painter.setPen(Qt.NoPen)
                painter.setBrush(color)
                radius = 2.2 if draw_mode == "points" else 1.8
                for point in mapped:
                    painter.drawEllipse(point, radius, radius)
        painter.restore()

    def _paint_channel_label(self, painter, plot_rect, visible_keys):
        key = self._hover_channel or (visible_keys[0] if visible_keys else "")
        if not key:
            return
        painter.save()
        painter.setPen(QColor(self.plot_widget.channel_color(key)))
        painter.drawText(plot_rect.adjusted(8, 6, -8, -8), Qt.AlignLeft | Qt.AlignTop, key)
        painter.restore()

    def _paint_live_tail_cursor(self, painter, plot_rect):
        if self.plot_widget.buffer.total_frames() == 0:
            return
        painter.save()
        x = self._live_tail_x(plot_rect)
        cursor_color = QColor("#c05cff")
        pen = QPen(cursor_color, 1.4, Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(int(x), int(plot_rect.top()), int(x), int(plot_rect.bottom()))

        label = _format_time_label(self.plot_widget.buffer.latest_time(), self.plot_widget.x_unit())
        metrics = QFontMetrics(painter.font())
        label_width = metrics.horizontalAdvance(label) + 12
        label_rect = QRectF(x - label_width / 2, plot_rect.bottom() + 4, label_width, 20)
        if label_rect.left() < plot_rect.left():
            label_rect.moveLeft(plot_rect.left())
        if label_rect.right() > plot_rect.right():
            label_rect.moveRight(plot_rect.right())
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#3a254d"))
        painter.drawRoundedRect(label_rect, 4, 4)
        painter.setPen(cursor_color)
        painter.drawText(label_rect, Qt.AlignCenter, label)
        painter.restore()

    def _paint_hover_crosshair(self, painter, plot_rect, start_s, end_s, y_min, y_max):
        if self._hover_pos is None or not plot_rect.contains(self._hover_pos):
            return
        painter.save()
        x = max(plot_rect.left(), min(plot_rect.right(), self._hover_pos.x()))
        y = max(plot_rect.top(), min(plot_rect.bottom(), self._hover_pos.y()))
        color = QColor("#ff4d4f")
        painter.setPen(QPen(color, 1.2, Qt.DashLine))
        painter.drawLine(int(x), int(plot_rect.top()), int(x), int(plot_rect.bottom()))
        painter.drawLine(int(plot_rect.left()), int(y), int(plot_rect.right()), int(y))

        hover_time = self._x_to_time(x)
        hover_value = self._y_to_value(y, plot_rect, y_min, y_max)
        x_label = _format_hover_time_label(hover_time, self.plot_widget.x_unit())
        y_label = f"{hover_value:.3f}"
        self._draw_axis_label(painter, x_label, x, plot_rect.bottom() + 5, color, horizontal=True, bounds=plot_rect)
        self._draw_axis_label(painter, y_label, plot_rect.left() - 6, y, color, horizontal=False, bounds=plot_rect)
        painter.restore()

    def _draw_axis_label(self, painter, text, x, y, color, horizontal=True, bounds=None):
        metrics = QFontMetrics(painter.font())
        width = metrics.horizontalAdvance(text) + 12
        height = 20
        if horizontal:
            rect = QRectF(x - width / 2, y, width, height)
            if bounds is not None:
                if rect.left() < bounds.left():
                    rect.moveLeft(bounds.left())
                if rect.right() > bounds.right():
                    rect.moveRight(bounds.right())
        else:
            rect = QRectF(x - width, y - height / 2, width, height)
            if rect.left() < 2:
                rect.moveLeft(2)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#2f2525"))
        painter.drawRoundedRect(rect, 4, 4)
        painter.setPen(color)
        painter.drawText(rect, Qt.AlignCenter, text)

    def _paint_tracer_marker(self, painter, x, plot_rect):
        style = self.plot_widget.tracer_style()
        y = plot_rect.center().y()
        painter.setPen(QPen(QColor("#c05cff"), 1.5))
        painter.setBrush(Qt.NoBrush)
        if style == "circle_slash":
            painter.drawEllipse(QRectF(x - 6, y - 6, 12, 12))
            painter.drawLine(int(x - 5), int(y + 5), int(x + 5), int(y - 5))
        elif style == "diamond_slash":
            points = [
                QPoint(int(x), int(y - 7)),
                QPoint(int(x + 7), int(y)),
                QPoint(int(x), int(y + 7)),
                QPoint(int(x - 7), int(y)),
            ]
            painter.drawPolygon(*points)
            painter.drawLine(int(x - 5), int(y + 5), int(x + 5), int(y - 5))
        else:
            painter.drawLine(int(x - 7), int(y), int(x + 7), int(y))
            painter.drawLine(int(x), int(y - 7), int(x), int(y + 7))
            painter.drawLine(int(plot_rect.left()), int(y), int(plot_rect.right()), int(y))

    def _paint_status(self, painter, plot_rect, visible_keys, start_s, end_s):
        painter.save()
        if len(self._fps_times) >= 2:
            elapsed = max(0.001, self._fps_times[-1] - self._fps_times[0])
            fps = (len(self._fps_times) - 1) / elapsed
        else:
            fps = 0.0
        points = self.plot_widget.buffer.visible_point_count(visible_keys, start_s, end_s)
        painter.setPen(QColor("#aeb7c2"))
        painter.drawText(
            plot_rect.adjusted(0, 6, -8, 0),
            Qt.AlignRight | Qt.AlignTop,
            f"FPS: {fps:.1f}\nPts: {points}",
        )
        painter.restore()

    def _map_point(self, timestamp, value, plot_rect, start_s, end_s, y_min, y_max):
        x = self._time_to_x(timestamp, plot_rect, start_s, end_s)
        y = self._value_to_y(value, plot_rect, y_min, y_max)
        return QPointFCompat(x, y)

    def _time_to_x(self, timestamp, plot_rect, start_s, end_s):
        span = max(0.000001, end_s - start_s)
        return plot_rect.left() + (timestamp - start_s) / span * plot_rect.width()

    def _x_to_time(self, x):
        start_s, end_s = self.current_view_range()
        plot_rect = self._plot_rect()
        ratio = 0.0 if plot_rect.width() <= 0 else (x - plot_rect.left()) / plot_rect.width()
        ratio = max(0.0, min(1.0, ratio))
        return start_s + (end_s - start_s) * ratio

    def _value_to_y(self, value, plot_rect, y_min, y_max):
        span = max(0.000001, y_max - y_min)
        return plot_rect.bottom() - (value - y_min) / span * plot_rect.height()

    def _y_to_value(self, y, plot_rect, y_min, y_max):
        span = max(0.000001, y_max - y_min)
        ratio = (plot_rect.bottom() - y) / max(1.0, plot_rect.height())
        ratio = max(0.0, min(1.0, ratio))
        return y_min + ratio * span

    def _live_tail_x(self, plot_rect):
        return plot_rect.left() + plot_rect.width() * self.live_tail_ratio

    def _is_near_live_tail(self, pos):
        if self.plot_widget.buffer.total_frames() == 0:
            return False
        plot_rect = self._plot_rect()
        if not plot_rect.adjusted(-8, -8, 8, 8).contains(pos):
            return False
        return abs(pos.x() - self._live_tail_x(plot_rect)) <= 8

    def _set_live_tail_from_x(self, x):
        plot_rect = self._plot_rect()
        if plot_rect.width() <= 1:
            return
        ratio = (x - plot_rect.left()) / plot_rect.width()
        self.live_tail_ratio = max(0.1, min(0.95, ratio))
        self.update()

    def _set_hover_pos(self, pos):
        plot_rect = self._plot_rect()
        if plot_rect.contains(pos):
            self._hover_pos = pos
        else:
            self._hover_pos = None
        self.update()

    def _zoom_y_axis(self, pos, zoom_in):
        plot_rect = self._plot_rect()
        start_s, end_s = self.current_view_range()
        visible_keys = self.plot_widget.visible_channel_keys()
        if self.plot_widget.auto_range():
            y_min, y_max = self.plot_widget.buffer.y_range(visible_keys, start_s, end_s)
        else:
            y_min, y_max = self._last_y_range
        span = max(0.000001, y_max - y_min)
        speed = self.plot_widget.wheel_speed()
        new_span = span * (1.0 - speed if zoom_in else 1.0 + speed)
        center = self._y_to_value(pos.y(), plot_rect, y_min, y_max)
        ratio = (center - y_min) / span
        new_min = center - ratio * new_span
        new_max = new_min + new_span
        self._last_y_range = (new_min, new_max)
        self.plot_widget.set_auto_range(False)
        self.update()

    def _update_hover_channel(self, pos):
        start_s, end_s = self.current_view_range()
        plot_rect = self._plot_rect()
        y_min, y_max = self._last_y_range
        best_key = None
        best_distance = 10.0
        mouse_t = self._x_to_time(pos.x())
        for key in self.plot_widget.visible_channel_keys():
            points = self.plot_widget.buffer.series(key, start_s, end_s)
            if not points:
                continue
            timestamp, value = min(points, key=lambda item: abs(item[0] - mouse_t))
            x = self._time_to_x(timestamp, plot_rect, start_s, end_s)
            y = self._value_to_y(value, plot_rect, y_min, y_max)
            distance = math.hypot(pos.x() - x, pos.y() - y)
            if distance < best_distance:
                best_key = key
                best_distance = distance
        if best_key != self._hover_channel:
            self._hover_channel = best_key
            self.update()


class RealtimePlotWidget(QWidget):
    visible_channels_changed = pyqtSignal()

    def __init__(self, channel_manager=None, parent=None):
        super().__init__(parent)
        self.setObjectName("RealtimePlotWidget")
        self.channel_manager = channel_manager
        self.buffer = PlotDataBuffer(max_points=10000)
        self._started_at = None
        self._channels = {}
        self._visible_channels = set()
        self._visibility_configured = False
        self._auto_range = True
        self._draw_mode = "line"
        self._tracer_style = "cross_horizontal"
        self._x_unit = "ms"
        self._wheel_speed = 0.20
        self._cursor_value_mode = "nearest"
        self._demo_phase = 0.0
        self._paint_dirty = False
        self._build_ui()
        self._connect_signals()
        if self.channel_manager is not None:
            self.channel_manager.channels_changed.connect(self._handle_channels_changed)
            self._handle_channels_changed(self.channel_manager.channels())

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.toolbar_frame = QFrame(self)
        self.toolbar_frame.setObjectName("plotRealtimeToolbarFrame")
        toolbar = QHBoxLayout(self.toolbar_frame)
        toolbar.setContentsMargins(8, 6, 8, 6)
        toolbar.setSpacing(6)

        self.channel_combo = QComboBox(self.toolbar_frame)
        self.channel_combo.setObjectName("plotCompactComboBox")
        self.channel_combo.setFixedWidth(150)
        self.channel_combo.addItem("无通道")
        toolbar.addWidget(self.channel_combo)

        self.fft_combo = QComboBox(self.toolbar_frame)
        self.fft_combo.setObjectName("plotCompactComboBox")
        self.fft_combo.addItem("FFT: 暂未实现")
        self.fft_combo.setEnabled(False)
        self.fft_combo.setFixedWidth(132)
        toolbar.addWidget(self.fft_combo)

        toolbar.addWidget(QLabel("T:", self.toolbar_frame))
        self.time_spin = QDoubleSpinBox(self.toolbar_frame)
        self.time_spin.setRange(0.1, 120.0)
        self.time_spin.setSingleStep(0.5)
        self.time_spin.setDecimals(1)
        self.time_spin.setSuffix(" s")
        self.time_spin.setValue(10.0)
        self.time_spin.setFixedWidth(86)
        toolbar.addWidget(self.time_spin)

        toolbar.addWidget(QLabel("N:", self.toolbar_frame))
        self.max_points_spin = QSpinBox(self.toolbar_frame)
        self.max_points_spin.setRange(100, 200000)
        self.max_points_spin.setSingleStep(1000)
        self.max_points_spin.setValue(10000)
        self.max_points_spin.setFixedWidth(104)
        toolbar.addWidget(self.max_points_spin)

        self.auto_range_button = QToolButton(self.toolbar_frame)
        self.auto_range_button.setText("自动范围")
        self.auto_range_button.setCheckable(True)
        self.auto_range_button.setChecked(True)
        toolbar.addWidget(self.auto_range_button)

        self.demo_button = QToolButton(self.toolbar_frame)
        self.demo_button.setText("Demo")
        self.demo_button.setCheckable(True)
        toolbar.addWidget(self.demo_button)

        self.hide_toolbar_button = QToolButton(self.toolbar_frame)
        self.hide_toolbar_button.setText("隐藏工具栏")
        toolbar.addWidget(self.hide_toolbar_button)
        toolbar.addStretch(1)

        layout.addWidget(self.toolbar_frame, 0)
        self.draw_area = PlotDrawArea(self, self)
        self.draw_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.draw_area, 1)

        self.demo_timer = QTimer(self)
        self.demo_timer.setInterval(30)
        self.repaint_timer = QTimer(self)
        self.repaint_timer.setInterval(33)
        self.repaint_timer.start()

    def _connect_signals(self):
        self.time_spin.valueChanged.connect(lambda value: self.set_time_window_s(value))
        self.max_points_spin.valueChanged.connect(self._set_max_points)
        self.auto_range_button.toggled.connect(self.set_auto_range)
        self.hide_toolbar_button.clicked.connect(lambda: self.set_toolbar_visible(False))
        self.demo_button.toggled.connect(self._set_demo_enabled)
        self.demo_timer.timeout.connect(self._append_demo_frame)
        self.repaint_timer.timeout.connect(self._update_if_dirty)
        self.draw_area.context_menu_requested.connect(self.show_context_menu)

    def _handle_channels_changed(self, channels):
        channels = list(channels or [])
        values = {}
        for channel in channels:
            self._channels[channel.key] = channel
            if not self._visibility_configured and channel.enabled:
                self._visible_channels.add(channel.key)
            if channel.enabled:
                values[channel.key] = channel.display_value
        if values:
            if self._started_at is None:
                self._started_at = time.perf_counter()
            self.buffer.append(time.perf_counter() - self._started_at, values)
        self._refresh_channel_summary()
        self._paint_dirty = True

    def _update_if_dirty(self):
        if not self._paint_dirty:
            return
        self._paint_dirty = False
        self.draw_area.update()

    def _append_demo_frame(self):
        if self.channel_manager is None:
            return
        self._demo_phase += 0.03
        t = self._demo_phase
        triangle_phase = (t * 0.35) % 1.0
        square_phase = (t * 0.45) % 1.0
        saw_phase = (t * 0.25) % 1.0
        triangle = 4.0 * abs(triangle_phase - 0.5) - 1.0
        square = 1.0 if square_phase < 0.5 else -1.0
        saw = 2.0 * saw_phase - 1.0
        sine = math.sin(2.0 * math.pi * 0.32 * t) + 0.35 * math.sin(2.0 * math.pi * 0.91 * t)
        self.channel_manager.update_values([triangle, square + 1.5, saw + 3.0, sine + 5.0])

    def _set_demo_enabled(self, enabled):
        if enabled:
            self.demo_timer.start()
        else:
            self.demo_timer.stop()

    def _set_max_points(self, value):
        self.buffer.set_max_points(value)
        self.draw_area.update()

    def set_time_window_s(self, value, reset_view=True):
        value = max(0.1, min(120.0, float(value)))
        self.time_spin.blockSignals(True)
        self.time_spin.setValue(value)
        self.time_spin.blockSignals(False)
        if reset_view:
            self.draw_area.reset_view_to_latest()
        self.draw_area.update()

    def time_window_s(self):
        return float(self.time_spin.value())

    def set_auto_range(self, enabled):
        self._auto_range = bool(enabled)
        self.auto_range_button.blockSignals(True)
        self.auto_range_button.setChecked(self._auto_range)
        self.auto_range_button.blockSignals(False)
        self.draw_area.update()

    def auto_range(self):
        return self._auto_range

    def set_toolbar_visible(self, visible):
        self.toolbar_frame.setVisible(bool(visible))

    def toolbar_visible(self):
        return self.toolbar_frame.isVisible()

    def visible_channel_keys(self):
        keys = [key for key in self._channels.keys() if self.is_channel_visible(key)]
        return sorted(keys, key=_channel_sort_key)

    def is_channel_visible(self, key):
        return key in self._visible_channels

    def set_channel_visible(self, key, visible):
        self._visibility_configured = True
        if visible:
            self._visible_channels.add(key)
        else:
            self._visible_channels.discard(key)
        self._refresh_channel_summary()
        self.visible_channels_changed.emit()
        self.draw_area.update()

    def set_all_channels_visible(self, visible):
        self._visibility_configured = True
        if visible:
            self._visible_channels = set(self._channels.keys())
        else:
            self._visible_channels.clear()
        self._refresh_channel_summary()
        self.visible_channels_changed.emit()
        self.draw_area.update()

    def toggle_channel_visible(self, key):
        self.set_channel_visible(key, not self.is_channel_visible(key))

    def channel_color(self, key):
        channel = self._channels.get(key)
        if channel is not None and channel.color:
            return channel.color
        index = _channel_sort_key(key)[0]
        return DEFAULT_CHANNEL_COLORS[index % len(DEFAULT_CHANNEL_COLORS)]

    def draw_mode(self):
        return self._draw_mode

    def tracer_style(self):
        return self._tracer_style

    def x_unit(self):
        return self._x_unit

    def wheel_speed(self):
        return self._wheel_speed

    def cursor_value_mode(self):
        return self._cursor_value_mode

    def clear_data(self):
        self.buffer.clear()
        self._started_at = None
        self.draw_area.reset_view_to_latest()
        self.draw_area.update()

    def to_dict(self):
        return {
            "visible_channels": self.visible_channel_keys(),
            "auto_range": self._auto_range,
            "time_window_s": self.time_window_s(),
            "max_points": self.buffer.max_points(),
            "draw_mode": self._draw_mode,
            "tracer_style": self._tracer_style,
            "x_unit": self._x_unit,
            "wheel_speed": self._wheel_speed,
            "cursor_value_mode": self._cursor_value_mode,
            "toolbar_visible": self.toolbar_visible(),
            "live_tail_ratio": self.draw_area.live_tail_ratio,
        }

    def apply_config(self, config):
        config = dict(config or {})
        visible = config.get("visible_channels")
        if isinstance(visible, list) and visible:
            self._visibility_configured = True
            self._visible_channels = {str(key) for key in visible}
        elif isinstance(visible, list):
            self._visibility_configured = False
            self._visible_channels.clear()
        self.set_auto_range(bool(config.get("auto_range", True)))
        self.set_time_window_s(float(config.get("time_window_s", 10.0)))
        self.max_points_spin.setValue(int(config.get("max_points", 10000)))
        self._draw_mode = config.get("draw_mode", "line") if config.get("draw_mode", "line") in DRAW_MODES else "line"
        self._tracer_style = (
            config.get("tracer_style", "cross_horizontal")
            if config.get("tracer_style", "cross_horizontal") in TRACER_STYLES
            else "cross_horizontal"
        )
        self._x_unit = config.get("x_unit", "ms") if config.get("x_unit", "ms") in X_UNITS else "ms"
        self._wheel_speed = float(config.get("wheel_speed", 0.20))
        if self._wheel_speed not in WHEEL_SPEEDS:
            self._wheel_speed = 0.20
        self._cursor_value_mode = (
            config.get("cursor_value_mode", "nearest")
            if config.get("cursor_value_mode", "nearest") in CURSOR_VALUE_MODES
            else "nearest"
        )
        self.draw_area.live_tail_ratio = max(0.1, min(0.95, float(config.get("live_tail_ratio", 0.78))))
        self.set_toolbar_visible(bool(config.get("toolbar_visible", True)))
        self._refresh_channel_summary()
        self.visible_channels_changed.emit()
        self.draw_area.update()

    def show_context_menu(self, global_pos):
        menu = QMenu(self)
        menu.setObjectName("plotContextMenu")

        channel_menu = menu.addMenu("通道配置")
        channel_menu.setObjectName("plotContextMenu")
        all_action = channel_menu.addAction("All")
        all_action.setCheckable(True)
        channel_keys = sorted(self._channels.keys(), key=_channel_sort_key)
        all_action.setChecked(bool(channel_keys) and all(self.is_channel_visible(key) for key in channel_keys))
        channel_actions = {}
        for key in channel_keys:
            action = channel_menu.addAction(key)
            action.setCheckable(True)
            action.setChecked(self.is_channel_visible(key))
            channel_actions[action] = key

        auto_action = menu.addAction("自动范围")
        auto_action.setCheckable(True)
        auto_action.setChecked(self._auto_range)
        save_action = menu.addAction("保存数据")
        toolbar_action = menu.addAction("隐藏工具栏" if self.toolbar_visible() else "显示工具栏")
        copy_action = menu.addAction("复制截图")
        copy_all_action = menu.addAction("复制所有截图")
        menu.addSeparator()

        draw_menu = menu.addMenu("绘图模式")
        draw_menu.setObjectName("plotContextMenu")
        draw_actions = self._add_exclusive_actions(draw_menu, DRAW_MODES, self._draw_mode)
        tracer_menu = menu.addMenu("Tracer标记")
        tracer_menu.setObjectName("plotContextMenu")
        tracer_actions = self._add_exclusive_actions(tracer_menu, TRACER_STYLES, self._tracer_style)
        unit_menu = menu.addMenu("X轴单位")
        unit_menu.setObjectName("plotContextMenu")
        unit_actions = self._add_exclusive_actions(unit_menu, {key: label for key, (label, _scale) in X_UNITS.items()}, self._x_unit)
        speed_menu = menu.addMenu("滚轮速度")
        speed_menu.setObjectName("plotContextMenu")
        speed_actions = self._add_exclusive_actions(speed_menu, WHEEL_SPEEDS, self._wheel_speed)
        cursor_menu = menu.addMenu("光标取值方式")
        cursor_menu.setObjectName("plotContextMenu")
        cursor_actions = self._add_exclusive_actions(cursor_menu, CURSOR_VALUE_MODES, self._cursor_value_mode)

        action = menu.exec_(global_pos)
        if action is None:
            return
        if action == all_action:
            self.set_all_channels_visible(all_action.isChecked())
        elif action in channel_actions:
            self.set_channel_visible(channel_actions[action], action.isChecked())
        elif action == auto_action:
            self.set_auto_range(auto_action.isChecked())
        elif action == save_action:
            self.save_data()
        elif action == toolbar_action:
            self.set_toolbar_visible(not self.toolbar_visible())
        elif action == copy_action:
            self.copy_screenshot(all_widgets=False)
        elif action == copy_all_action:
            self.copy_screenshot(all_widgets=True)
        elif action in draw_actions:
            self._draw_mode = draw_actions[action]
            self.draw_area.update()
        elif action in tracer_actions:
            self._tracer_style = tracer_actions[action]
            self.draw_area.update()
        elif action in unit_actions:
            self._x_unit = unit_actions[action]
            self.draw_area.update()
        elif action in speed_actions:
            self._wheel_speed = speed_actions[action]
        elif action in cursor_actions:
            self._cursor_value_mode = cursor_actions[action]

    def save_data(self):
        default_dir = Path("config/plot_data")
        default_dir.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存绘图数据",
            str(default_dir / "plot_data.csv"),
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return
        self.buffer.export_csv(path, self._export_channel_keys())

    def copy_screenshot(self, all_widgets=False):
        widget = self._screenshot_root() if all_widgets else self.draw_area
        pixmap = widget.grab() if widget is not None else QPixmap()
        QApplication.clipboard().setPixmap(pixmap)

    def _screenshot_root(self):
        widget = self
        while widget.parentWidget() is not None:
            if widget.parentWidget().__class__.__name__ == "PlotWorkspacePage":
                return widget.parentWidget()
            widget = widget.parentWidget()
        return self

    def _add_exclusive_actions(self, menu, choices, current):
        actions = {}
        for value, label in choices.items():
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(value == current)
            actions[action] = value
        return actions

    def _refresh_channel_summary(self):
        visible = self.visible_channel_keys()
        text = ",".join(visible) if visible else "无通道"
        self.channel_combo.blockSignals(True)
        self.channel_combo.clear()
        self.channel_combo.addItem(text)
        self.channel_combo.blockSignals(False)

    def _export_channel_keys(self):
        keys = set(self._channels.keys())
        keys.update(self.buffer.channel_keys())
        return sorted(keys, key=_channel_sort_key)


def _format_axis(value):
    abs_value = abs(value)
    if abs_value >= 1000:
        return f"{value:.0f}"
    if abs_value >= 10:
        return f"{value:.1f}"
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _format_csv_value(value):
    if value is None:
        return ""
    return f"{float(value):.9g}"


def _format_time_label(timestamp_s, unit):
    if unit == "s":
        return f"{timestamp_s:.3f}s"
    if unit == "us":
        return f"{timestamp_s * 1000000.0:.0f}us"
    return f"{timestamp_s * 1000.0:.0f}"


def _format_hover_time_label(timestamp_s, unit):
    if unit == "s":
        return f"{timestamp_s:.3f}s"
    if unit == "us":
        return f"{timestamp_s * 1000000.0:.0f}us"
    return f"{timestamp_s * 1000.0:.3f}"


def _linear_value(points, cursor_s):
    if cursor_s <= points[0][0]:
        return points[0][1]
    if cursor_s >= points[-1][0]:
        return points[-1][1]
    for index in range(1, len(points)):
        left_t, left_v = points[index - 1]
        right_t, right_v = points[index]
        if left_t <= cursor_s <= right_t:
            span = right_t - left_t
            if span <= 0:
                return left_v
            ratio = (cursor_s - left_t) / span
            return left_v + (right_v - left_v) * ratio
    return points[-1][1]


def _decimate_points(points, max_points):
    if len(points) <= max_points:
        return points
    step = int(math.ceil(len(points) / max(1, max_points)))
    decimated = points[::step]
    if decimated[-1] != points[-1]:
        decimated.append(points[-1])
    return decimated


def _channel_sort_key(key):
    text = str(key)
    if text.upper().startswith("CH"):
        try:
            return int(text[2:]), text
        except ValueError:
            pass
    return 999999, text


def QPointFCompat(x, y):
    from PyQt5.QtCore import QPointF

    return QPointF(float(x), float(y))
