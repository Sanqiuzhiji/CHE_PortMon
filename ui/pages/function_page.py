# -*- coding: utf-8 -*-
from pathlib import Path

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout, QWidget

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.font_manager import FontProperties
from matplotlib.figure import Figure

from ui.generated.function_page_ui import Ui_FunctionPage


def _cjk_font_properties():
    for font_path in (
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyh.ttf",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ):
        path = Path(font_path)
        if path.exists():
            return FontProperties(fname=str(path))
    return None


class FunctionPage(QWidget):
    preview_requested = pyqtSignal()
    send_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ui = Ui_FunctionPage()
        self.ui.setupUi(self)
        self._sending = False
        self._title_font = _cjk_font_properties()
        self.ui.functionComboBox.addItems(["正弦", "余弦", "正切", "方波", "三角波", "锯齿波", "指数", "对数"])
        self.figure = Figure(figsize=(6, 4), dpi=90)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.grid(True, alpha=0.3)
        self._set_chart_title("函数预览", "Function Preview")
        chart_layout = QVBoxLayout(self.ui.chartContainer)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.addWidget(self.canvas)
        self.ui.previewButton.clicked.connect(self.preview_requested)
        self.ui.sendFunctionButton.clicked.connect(self._send_or_stop)

    def get_parameters(self):
        return {
            "function_name": self.ui.functionComboBox.currentText(),
            "start": float(self.ui.startLineEdit.text()),
            "end": float(self.ui.endLineEdit.text()),
            "step": float(self.ui.stepLineEdit.text()),
            "amplitude": float(self.ui.amplitudeLineEdit.text()),
            "frequency": float(self.ui.frequencyLineEdit.text()),
            "period_ms": self.period_ms(),
        }

    def period_ms(self):
        try:
            return max(10, int(self.ui.periodLineEdit.text().strip() or "1000"))
        except ValueError:
            return 1000

    def plot_points(self, points):
        x_values = [point[0] for point in points]
        y_values = [point[1] for point in points]
        self.ax.clear()
        self.ax.grid(True, alpha=0.3)
        self.ax.plot(x_values, y_values, color="#2f80ed", linewidth=2)
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self._set_chart_title(f"{self.ui.functionComboBox.currentText()} 预览", "Function Preview")
        self.canvas.draw()

    def set_sending(self, sending):
        self._sending = sending
        self.ui.sendFunctionButton.setText("停止发送" if sending else "发送函数数据")

    def _send_or_stop(self):
        if self._sending:
            self.stop_requested.emit()
        else:
            self.send_requested.emit()

    def _set_chart_title(self, title, fallback_title):
        if self._title_font is None:
            self.ax.set_title(fallback_title)
            return
        self.ax.set_title(title, fontproperties=self._title_font)
