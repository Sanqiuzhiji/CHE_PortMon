# -*- coding: utf-8 -*-
from pathlib import Path

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from services.config_service import ConfigService
from services.serial_service import SerialService
from ui.generated.main_window_ui import Ui_MainWindow
from ui.pages.connection_page import ConnectionPage
from ui.pages.function_page import FunctionPage
from ui.pages.monitor_page import MonitorPage
from ui.pages.send_page import SendPage
from ui.pages.settings_page import SettingsPage
from utils.file_utils import read_binary_file, save_text_file
from utils.format_utils import format_received_data, hex_to_bytes, text_to_bytes
from utils.function_generator import generate_function_points


class MainWindow(QMainWindow):
    """Assembles generated UI pages and coordinates services."""

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.serial_service = SerialService()
        self.config_service = ConfigService()
        self.settings = self.config_service.load_settings()
        self.current_port = "-"
        self.current_baud = "-"
        self.connected = False
        self.function_points = []
        self.function_index = 0

        self.auto_send_timer = QTimer(self)
        self.auto_send_timer.timeout.connect(self._send_current_payload)
        self.function_send_timer = QTimer(self)
        self.function_send_timer.timeout.connect(self._send_next_function_point)

        self._create_pages()
        self._connect_signals()
        self._apply_styles()
        self._apply_settings()
        self._refresh_ports()
        self._select_page(0)
        self._update_status()

    def _create_pages(self):
        self.connection_page = ConnectionPage()
        self.monitor_page = MonitorPage()
        self.send_page = SendPage()
        self.function_page = FunctionPage()
        self.settings_page = SettingsPage()

        for page in (
            self.connection_page,
            self.monitor_page,
            self.send_page,
            self.function_page,
            self.settings_page,
        ):
            self.ui.pageStack.addWidget(page)

    def _connect_signals(self):
        nav_pairs = [
            (self.ui.connectionNavButton, 0),
            (self.ui.monitorNavButton, 1),
            (self.ui.sendNavButton, 2),
            (self.ui.functionNavButton, 3),
            (self.ui.settingsNavButton, 4),
        ]
        self.nav_buttons = [button for button, _ in nav_pairs]
        for button, index in nav_pairs:
            button.clicked.connect(lambda checked=False, page_index=index: self._select_page(page_index))

        self.serial_service.data_received.connect(self._handle_received_data)
        self.serial_service.opened.connect(self._handle_opened)
        self.serial_service.closed.connect(self._handle_closed)
        self.serial_service.error.connect(self._show_error)
        self.serial_service.stats_changed.connect(self._update_counts)

        self.connection_page.refresh_requested.connect(self._refresh_ports)
        self.connection_page.toggle_connection_requested.connect(self._toggle_connection)

        self.monitor_page.clear_requested.connect(self._clear_receive)
        self.monitor_page.save_requested.connect(self._save_receive_data)

        self.send_page.send_requested.connect(self._send_current_payload)
        self.send_page.auto_send_toggled.connect(self._set_auto_send)
        self.send_page.file_send_requested.connect(self._send_selected_file)

        self.function_page.preview_requested.connect(self._preview_function)
        self.function_page.send_requested.connect(self._start_function_send)
        self.function_page.stop_requested.connect(self._stop_function_send)

        self.settings_page.save_requested.connect(self._save_settings)

    def _apply_styles(self):
        if self.settings.theme == "浅色":
            self.setStyleSheet("")
            return
        style_path = Path(__file__).resolve().parents[1] / "ui" / "styles" / "dark.qss"
        self.setStyleSheet(style_path.read_text(encoding="utf-8") if style_path.exists() else "")

    def _apply_settings(self):
        self.connection_page.set_default_baudrate(self.settings.default_baudrate)
        self.monitor_page.set_default_save_path(self.settings.default_save_path)
        self.settings_page.set_settings(self.settings)
        if self.settings.auto_connect:
            QTimer.singleShot(100, self._toggle_connection)

    def _save_settings(self, settings):
        self.settings = settings
        self.config_service.save_settings(settings)
        self.connection_page.set_default_baudrate(settings.default_baudrate)
        self.monitor_page.set_default_save_path(settings.default_save_path)
        self._apply_styles()
        QMessageBox.information(self, "设置", "设置已保存")

    def _select_page(self, index):
        self.ui.pageStack.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setProperty("active", button_index == index)
            button.style().unpolish(button)
            button.style().polish(button)

    def _refresh_ports(self):
        self.connection_page.set_ports(self.serial_service.list_ports())

    def _toggle_connection(self):
        if self.serial_service.is_open():
            self.serial_service.close_port()
            return
        try:
            config = self.connection_page.get_config()
        except ValueError as exc:
            self._show_error(f"串口配置无效: {exc}")
            return
        self.current_port = config.port_name or "-"
        self.current_baud = str(config.baud_rate)
        self.serial_service.open_port(config)

    def _handle_opened(self):
        self.connected = True
        self.connection_page.set_connected(True)
        self._update_status()

    def _handle_closed(self):
        self.connected = False
        self.connection_page.set_connected(False)
        self._set_auto_send(False)
        self._stop_function_send()
        self._update_status()

    def _handle_received_data(self, data):
        options = self.monitor_page.get_options()
        if options.paused:
            return
        self.monitor_page.append_receive_data(
            format_received_data(data, hex_display=options.hex_display, timestamp=options.timestamp)
        )

    def _send_current_payload(self):
        try:
            payload = self._build_send_payload()
        except ValueError as exc:
            self._show_error(str(exc))
            self._set_auto_send(False)
            return
        self.serial_service.send_bytes(payload)

    def _build_send_payload(self):
        options = self.send_page.get_options()
        text = self.send_page.send_text()
        if options.hex_mode:
            return hex_to_bytes(text)
        return text_to_bytes(text, append_newline=options.append_newline)

    def _set_auto_send(self, enabled):
        if enabled:
            self.auto_send_timer.start(self.send_page.auto_interval_ms())
        else:
            self.auto_send_timer.stop()
        self.send_page.set_auto_sending(enabled)

    def _send_selected_file(self):
        path = self.send_page.selected_file_path()
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "选择要发送的文件", "", "所有文件 (*)")
            if not path:
                return
        try:
            self.serial_service.send_bytes(read_binary_file(path))
        except OSError as exc:
            self._show_error(f"读取文件失败: {exc}")

    def _clear_receive(self):
        self.monitor_page.clear_receive_data()
        self.serial_service.reset_receive_count()

    def _save_receive_data(self, path):
        try:
            save_text_file(path, self.monitor_page.receive_text())
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
        self.serial_service.send_bytes(text_to_bytes(f"{y_value:.6f}\n"))
        self.function_index += 1

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
