# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QFileDialog, QWidget

from models.serial_config import ReceiveOptions
from ui.generated.monitor_page_ui import Ui_MonitorPage


class MonitorPage(QWidget):
    options_changed = pyqtSignal()
    clear_requested = pyqtSignal()
    save_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.ui = Ui_MonitorPage()
        self.ui.setupUi(self)
        self.default_save_path = ""
        for item in (self.ui.hexCheckBox, self.ui.timestampCheckBox, self.ui.autoScrollCheckBox, self.ui.pauseCheckBox):
            item.stateChanged.connect(self.options_changed)
        self.ui.clearButton.clicked.connect(self.clear_requested)
        self.ui.saveButton.clicked.connect(self._select_save_path)

    def get_options(self):
        return ReceiveOptions(
            hex_display=self.ui.hexCheckBox.isChecked(),
            timestamp=self.ui.timestampCheckBox.isChecked(),
            auto_scroll=self.ui.autoScrollCheckBox.isChecked(),
            paused=self.ui.pauseCheckBox.isChecked(),
        )

    def append_receive_data(self, text):
        cursor = self.ui.receiveTextEdit.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.ui.receiveTextEdit.setTextCursor(cursor)
        if self.ui.autoScrollCheckBox.isChecked():
            self.ui.receiveTextEdit.ensureCursorVisible()

    def clear_receive_data(self):
        self.ui.receiveTextEdit.clear()

    def receive_text(self):
        return self.ui.receiveTextEdit.toPlainText()

    def set_default_save_path(self, path):
        self.default_save_path = path or ""

    def _select_save_path(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存接收数据",
            self.default_save_path,
            "文本文件 (*.txt);;所有文件 (*)",
        )
        if path:
            self.save_requested.emit(path)
