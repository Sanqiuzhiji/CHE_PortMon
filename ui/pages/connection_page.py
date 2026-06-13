# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)

from controllers.uart_controller import UartController
from ui.pages.uart_connection_page import UartConnectionPage
from ui.widgets.detachable_tab_widget import DetachableTabWidget


class ConnectionPage(QWidget):
    uart_status_changed = pyqtSignal(str, str, bool)
    uart_stats_changed = pyqtSignal(int, int)
    uart_error = pyqtSignal(str)

    def __init__(self, channel_manager=None):
        super().__init__()
        self.uart_widget = UartConnectionPage()
        self.uart_controller = UartController(self.uart_widget, channel_manager=channel_manager, parent=self)

        self._build_ui()
        self._connect_signals()
        self.register_connection("uart", "UART", self.uart_widget)

    def _build_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(18, 14, 18, 14)
        self.root_layout.setSpacing(10)

        self.title_label = QLabel("Connection", self)
        self.title_label.setObjectName("connectionTitleLabel")
        self.root_layout.addWidget(self.title_label)

        self.protocol_tabs = DetachableTabWidget(self)
        self.protocol_tabs.setObjectName("connectionProtocolTabs")
        self.root_layout.addWidget(self.protocol_tabs)

    def _connect_signals(self):
        self.uart_controller.status_changed.connect(self.uart_status_changed)
        self.uart_controller.stats_changed.connect(self.uart_stats_changed)
        self.uart_controller.error.connect(self.uart_error)

    def register_connection(self, key, title, page):
        return self.protocol_tabs.register_connection(key, title, page)

    def detach_uart(self):
        for index in range(self.protocol_tabs.count()):
            if self.protocol_tabs.tabBar().tabData(index) == "uart":
                self.protocol_tabs.detach_tab(index)
                return

    def set_default_baudrate(self, baudrate):
        self.uart_widget.set_default_baudrate(baudrate)

    def set_default_save_path(self, path):
        self.uart_widget.set_default_save_path(path)

    def refresh_ports(self):
        self.uart_controller.refresh_ports()

    def refresh_uart_protocols(self):
        self.uart_widget.refresh_protocol_options()

    def auto_connect_uart(self):
        self.uart_controller.auto_connect()
