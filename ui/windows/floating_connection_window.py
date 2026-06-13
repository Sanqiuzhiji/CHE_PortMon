# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QMainWindow


class FloatingConnectionWindow(QMainWindow):
    closed = pyqtSignal()

    def __init__(self, title, page, parent=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle(title)
        self.resize(1000, 720)
        self.setCentralWidget(page)
        page.show()

    def closeEvent(self, event):
        self.takeCentralWidget()
        self.closed.emit()
        super().closeEvent(event)
