# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QMainWindow


class FloatingPageWindow(QMainWindow):
    closed = pyqtSignal()

    def __init__(self, title, widget, parent=None):
        super().__init__(parent)
        self._widget = widget
        self.setWindowFlags(Qt.Window)
        self.setWindowTitle(title)
        self.setCentralWidget(widget)
        widget.show()
        self.resize(980, 680)

    def closeEvent(self, event):
        widget = self.takeCentralWidget()
        if widget is not None:
            widget.setParent(None)
        self.closed.emit()
        super().closeEvent(event)
