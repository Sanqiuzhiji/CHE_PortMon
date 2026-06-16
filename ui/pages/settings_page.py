# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtWidgets import QFileDialog, QLabel, QComboBox, QWidget

from models.app_settings import AppSettings, normalize_theme
from ui.generated.settings_page_ui import Ui_SettingsPage


class SettingsPage(QWidget):
    save_requested = pyqtSignal(object)

    COMMON_UI_FONTS = [
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "SimSun",
        "SimHei",
        "DengXian",
        "Segoe UI",
        "Arial",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
    ]

    THEME_LABELS = {
        "dark": "夜间模式",
        "light": "日间模式",
    }

    def __init__(self):
        super().__init__()
        self.ui = Ui_SettingsPage()
        self.ui.setupUi(self)
        self.ui.themeComboBox.addItem("夜间模式", "dark")
        self.ui.themeComboBox.addItem("日间模式", "light")
        self._init_font_options()
        self.ui.browseButton.clicked.connect(self._select_save_path)
        self.ui.saveSettingsButton.clicked.connect(self._emit_save)

    def _init_font_options(self):
        self.ui.fontLabel = QLabel("界面字体", self.ui.settingsGroup)
        self.ui.fontLabel.setObjectName("fontLabel")
        self.ui.fontComboBox = QComboBox(self.ui.settingsGroup)
        self.ui.fontComboBox.setObjectName("fontComboBox")
        self.ui.fontComboBox.addItem("System Default", "")

        installed = set(QFontDatabase().families())
        for font_name in self.COMMON_UI_FONTS:
            if font_name in installed:
                self.ui.fontComboBox.addItem(font_name, font_name)

        self.ui.formLayout.insertRow(1, self.ui.fontLabel, self.ui.fontComboBox)

    def set_settings(self, settings):
        theme = normalize_theme(settings.theme)
        index = self.ui.themeComboBox.findData(theme)
        self.ui.themeComboBox.setCurrentIndex(max(index, 0))
        font_name = getattr(settings, "ui_font", "")
        font_index = self.ui.fontComboBox.findData(font_name)
        if font_name and font_index < 0:
            self.ui.fontComboBox.addItem(font_name, font_name)
            font_index = self.ui.fontComboBox.findData(font_name)
        self.ui.fontComboBox.setCurrentIndex(max(font_index, 0))
        self.ui.defaultBaudLineEdit.setText(settings.default_baudrate)
        self.ui.autoConnectCheckBox.setChecked(settings.auto_connect)
        self.ui.savePathLineEdit.setText(settings.default_save_path)

    def get_settings(self):
        return AppSettings(
            theme=normalize_theme(self.ui.themeComboBox.currentData()),
            ui_font=self.ui.fontComboBox.currentData() or "",
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
