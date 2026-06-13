# -*- coding: utf-8 -*-
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox

from controllers.protocol_editor_controller import ProtocolEditorController
from services.config_service import ConfigService
from services.channel_manager import ChannelManager
from services.theme_service import ThemeService
from ui.generated.main_window_ui import Ui_MainWindow
from ui.pages.connection_page import ConnectionPage
from ui.pages.function_page import FunctionPage
from ui.pages.plot_page import PlotPage
from ui.pages.protocol_editor_page import ProtocolEditorPage
from ui.pages.settings_page import SettingsPage
from utils.format_utils import text_to_bytes
from utils.function_generator import generate_function_points


class MainWindow(QMainWindow):
    """Assembles generated UI pages and coordinates services."""

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.config_service = ConfigService()
        self.theme_service = ThemeService()
        self.settings = self.config_service.load_settings()
        self.current_port = "-"
        self.current_baud = "-"
        self.connected = False
        self.function_points = []
        self.function_index = 0
        self.function_send_timer = QTimer(self)
        self.function_send_timer.timeout.connect(self._send_next_function_point)
        self.channel_manager = ChannelManager(self)

        self._create_pages()
        self._connect_signals()
        self._apply_theme()
        self._apply_settings()
        self.connection_page.refresh_ports()
        self._select_page(0)
        self._update_status()

    def _create_pages(self):
        self.connection_page = ConnectionPage(channel_manager=self.channel_manager)
        self.plot_page = PlotPage(channel_manager=self.channel_manager)
        self.protocol_editor_page = ProtocolEditorPage()
        self.protocol_editor_controller = ProtocolEditorController(self.protocol_editor_page)
        self.function_page = FunctionPage()
        self.settings_page = SettingsPage()
        self.uart_controller = self.connection_page.uart_controller

        for page in (self.connection_page, self.plot_page, self.protocol_editor_page, self.function_page, self.settings_page):
            self.ui.pageStack.addWidget(page)

    def _connect_signals(self):
        nav_pairs = [
            (self.ui.connectionNavButton, 0),
            (self.ui.plotNavButton, 1),
            (self.ui.protocolEditorNavButton, 2),
            (self.ui.functionNavButton, 3),
            (self.ui.settingsNavButton, 4),
        ]
        self.nav_buttons = [button for button, _ in nav_pairs]
        for button, index in nav_pairs:
            button.clicked.connect(lambda checked=False, page_index=index: self._select_page(page_index))

        self.connection_page.uart_status_changed.connect(self._handle_uart_status_changed)
        self.connection_page.uart_stats_changed.connect(self._update_counts)
        self.connection_page.uart_error.connect(self._show_error)

        self.function_page.preview_requested.connect(self._preview_function)
        self.function_page.send_requested.connect(self._start_function_send)
        self.function_page.stop_requested.connect(self._stop_function_send)
        self.plot_page.command_generated.connect(self._send_plot_command)

        self.settings_page.save_requested.connect(self._save_settings)

    def _apply_theme(self):
        app = QApplication.instance()
        if app is not None:
            self.settings.theme = self.theme_service.apply_theme(app, self.settings.theme)
        else:
            self.settings.theme = self.theme_service.apply_theme(self, self.settings.theme)

    def _apply_settings(self):
        self.connection_page.set_default_baudrate(self.settings.default_baudrate)
        self.connection_page.set_default_save_path(self.settings.default_save_path)
        self.settings_page.set_settings(self.settings)
        if self.settings.auto_connect:
            self.connection_page.auto_connect_uart()

    def _save_settings(self, settings):
        self.settings = settings
        self._apply_theme()
        self.config_service.save_settings(self.settings)
        self.connection_page.set_default_baudrate(self.settings.default_baudrate)
        self.connection_page.set_default_save_path(self.settings.default_save_path)
        self.settings_page.set_settings(self.settings)
        QMessageBox.information(self, "设置", "设置已保存")

    def _select_page(self, index):
        if index == 0:
            self.connection_page.refresh_uart_protocols()
        self.ui.pageStack.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setProperty("active", button_index == index)
            button.style().unpolish(button)
            button.style().polish(button)

    def _handle_uart_status_changed(self, port, baud, connected):
        self.current_port = port
        self.current_baud = baud
        self.connected = connected
        if not connected:
            self._stop_function_send()
        self._update_status()

    def _save_receive_data(self, path):
        try:
            self.uart_controller.save_receive_data(path)
        except OSError as exc:
            self._show_error(f"保存接收数据失败: {exc}")

    def _preview_function(self):
        try:
            params = self.function_page.get_parameters()
            points = generate_function_points(
                params["function_name"],
                params["start"],
                params["end"],
                params["step"],
                params["amplitude"],
                params["frequency"],
            )
            self.function_points = points
            self.function_page.plot_points(points)
        except ValueError as exc:
            self._show_error(str(exc))

    def _start_function_send(self):
        if not self.uart_controller.is_open():
            self._show_error("请先打开串口")
            return
        if not self.function_points:
            self._preview_function()
        if not self.function_points:
            return
        self.function_index = 0
        self.function_page.set_sending(True)
        self.function_send_timer.start(self.function_page.period_ms())

    def _send_next_function_point(self):
        if self.function_index >= len(self.function_points):
            self._stop_function_send()
            return
        _, y_value = self.function_points[self.function_index]
        self._send_uart_payload(f"{y_value:.6f}\n")
        self.function_index += 1

    def _send_uart_payload(self, payload):
        if not self.uart_controller.is_open():
            self._show_error("请先打开串口")
            return
        if isinstance(payload, bytes):
            data = payload
        else:
            data = text_to_bytes(str(payload))
        self.uart_controller.send_bytes(data)

    def _send_plot_command(self, payload):
        if not self.uart_controller.is_open():
            self._show_error("请先打开串口")
            return

        repeat_count = max(1, int(getattr(payload, "repeat_count", 1)))
        raw_payload = getattr(payload, "payload", payload)
        if isinstance(raw_payload, bytes):
            data = raw_payload
        else:
            data = text_to_bytes(str(raw_payload))

        for _ in range(repeat_count):
            if not self.uart_controller.send_bytes(data):
                break

    def _stop_function_send(self):
        self.function_send_timer.stop()
        self.function_page.set_sending(False)

    def _update_counts(self, receive_count, send_count):
        self.ui.receiveCountLabel.setText(f"接收: {receive_count} B")
        self.ui.sendCountLabel.setText(f"发送: {send_count} B")
        self._update_status()

    def _update_status(self):
        self.ui.portStatusLabel.setText(f"串口: {self.current_port}")
        self.ui.baudStatusLabel.setText(f"波特率: {self.current_baud}")
        self.ui.connectionStatusLabel.setText(f"状态: {'已连接' if self.connected else '未连接'}")

    def _show_error(self, message):
        QMessageBox.warning(self, "提示", message)
