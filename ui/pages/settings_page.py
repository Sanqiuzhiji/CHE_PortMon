# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QWidget

from models.app_settings import AppSettings
from ui.generated.settings_page_ui import Ui_SettingsPage


class SettingsPage(QWidget):
    save_requested = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.ui = Ui_SettingsPage()
        self.ui.setupUi(self)
        self.ui.themeComboBox.addItems(["深色", "浅色"])
        self.ui.browseButton.clicked.connect(self._select_save_path)
        self.ui.saveSettingsButton.clicked.connect(self._emit_save)

    def set_settings(self, settings):
        index = self.ui.themeComboBox.findText(settings.theme)
        self.ui.themeComboBox.setCurrentIndex(max(index, 0))
        self.ui.defaultBaudLineEdit.setText(settings.default_baudrate)
        self.ui.autoConnectCheckBox.setChecked(settings.auto_connect)
        self.ui.savePathLineEdit.setText(settings.default_save_path)

    def get_settings(self):
        return AppSettings(
            theme=self.ui.themeComboBox.currentText(),
            default_baudrate=self.ui.defaultBaudLineEdit.text().strip() or "115200",
            auto_connect=self.ui.autoConnectCheckBox.isChecked(),
            default_save_path=self.ui.savePathLineEdit.text().strip(),
        )

    def _select_save_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择默认保存路径")
        if path:
            self.ui.savePathLineEdit.setText(path)

    def _emit_save(self):
        self.save_requested.emit(self.get_settings())
