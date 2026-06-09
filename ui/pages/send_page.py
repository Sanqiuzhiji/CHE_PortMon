# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QWidget

from models.serial_config import SendOptions
from ui.generated.send_page_ui import Ui_SendPage


class SendPage(QWidget):
    send_requested = pyqtSignal()
    auto_send_toggled = pyqtSignal(bool)
    file_selected = pyqtSignal(str)
    file_send_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ui = Ui_SendPage()
        self.ui.setupUi(self)
        self.ui.sendButton.clicked.connect(self.send_requested)
        self.ui.autoButton.clicked.connect(self._toggle_auto_send)
        self.ui.clearButton.clicked.connect(self.ui.sendTextEdit.clear)
        self.ui.openFileButton.clicked.connect(self._select_file)
        self.ui.sendFileButton.clicked.connect(self.file_send_requested)

    def get_options(self):
        return SendOptions(
            hex_mode=self.ui.hexModeRadioButton.isChecked(),
            append_newline=self.ui.appendNewlineCheckBox.isChecked(),
            auto_interval_ms=self.auto_interval_ms(),
        )

    def send_text(self):
        return self.ui.sendTextEdit.toPlainText()

    def auto_interval_ms(self):
        try:
            return max(10, int(self.ui.intervalLineEdit.text().strip() or "1000"))
        except ValueError:
            return 1000

    def selected_file_path(self):
        return self.ui.filePathLineEdit.text().strip()

    def set_auto_sending(self, enabled):
        self.ui.autoButton.setText("停止自动发送" if enabled else "启动自动发送")

    def _toggle_auto_send(self):
        self.auto_send_toggled.emit(self.ui.autoButton.text() != "停止自动发送")

    def _select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择要发送的文件", "", "所有文件 (*)")
        if path:
            self.ui.filePathLineEdit.setText(path)
            self.file_selected.emit(path)
