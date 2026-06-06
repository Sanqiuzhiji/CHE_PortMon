# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from Serial_Port.app_SerialWindows import SerialAppClass


class MainWindow(QMainWindow):
    """Application shell with navigation and page container."""

    def __init__(self, window_manager):
        super().__init__()
        self.window_manager = window_manager

        self.setWindowTitle("CHE Port Monitor")
        self.resize(1280, 860)

        self.nav_buttons = []
        self.pages = QStackedWidget()

        central_widget = QWidget()
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        nav = self._create_navigation()
        root_layout.addWidget(nav)
        root_layout.addWidget(self.pages, 1)

        self.setCentralWidget(central_widget)
        self._create_pages()
        self._select_page(0)

    def _create_navigation(self):
        nav = QFrame()
        nav.setObjectName("mainNavigation")
        nav.setFixedWidth(180)
        nav.setStyleSheet(
            """
            QFrame#mainNavigation {
                background: #20242b;
            }
            QPushButton {
                border: 0;
                color: #e8edf2;
                font-size: 14px;
                padding: 12px 16px;
                text-align: left;
            }
            QPushButton:hover {
                background: #2d333d;
            }
            QPushButton[active="true"] {
                background: #3a4656;
                font-weight: 600;
            }
            """
        )

        layout = QVBoxLayout(nav)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(4)

        for index, text in enumerate(["旧版串口助手", "连接", "监视", "发送", "函数发生器"]):
            button = QPushButton(text)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, page_index=index: self._select_page(page_index))
            self.nav_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch(1)
        return nav

    def _create_pages(self):
        self.legacy_serial_page = SerialAppClass(self.window_manager)
        self.pages.addWidget(self.legacy_serial_page)
        self.pages.addWidget(self._placeholder_page("连接"))
        self.pages.addWidget(self._placeholder_page("监视"))
        self.pages.addWidget(self._placeholder_page("发送"))
        self.pages.addWidget(self._placeholder_page("函数发生器"))

    def _placeholder_page(self, title):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel(f"{title} 页面占位")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 24px; color: #555;")
        layout.addWidget(label)

        return page

    def _select_page(self, index):
        self.pages.setCurrentIndex(index)

        for button_index, button in enumerate(self.nav_buttons):
            is_active = button_index == index
            button.setProperty("active", is_active)
            button.style().unpolish(button)
            button.style().polish(button)
