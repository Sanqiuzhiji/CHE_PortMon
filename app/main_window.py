# -*- coding: utf-8 -*-
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox

from services.config_service import ConfigService
from services.port_scan_thread import PortScanThread
from services.serial_service import SerialService
from services.theme_service import ThemeService
from ui.generated.main_window_ui import Ui_MainWindow
from ui.pages.function_page import FunctionPage
from ui.pages.serial_page import SerialPage
from ui.pages.settings_page import SettingsPage
from utils.file_utils import save_text_file
from utils.format_utils import text_to_bytes
from utils.function_generator import generate_function_points


class MainWindow(QMainWindow):
    """Assembles generated UI pages and coordinates services."""

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.serial_service = SerialService()
        self.config_service = ConfigService()
        self.theme_service = ThemeService()
        self.settings = self.config_service.load_settings()
        self.current_port = "-"
        self.current_baud = "-"
        self.connected = False
        self.function_points = []
        self.function_index = 0
        self.port_scan_thread = None

        self.function_send_timer = QTimer(self)
        self.function_send_timer.timeout.connect(self._send_next_function_point)

        self._create_pages()
        self._connect_signals()
        self._apply_theme()
        self._apply_settings()
        self._refresh_ports()
        self._select_page(0)
        self._update_status()

    def _create_pages(self):
        self.serial_page = SerialPage()
        self.function_page = FunctionPage()
        self.settings_page = SettingsPage()

        for page in (self.serial_page, self.function_page, self.settings_page):
            self.ui.pageStack.addWidget(page)

    def _connect_signals(self):
        nav_pairs = [
            (self.ui.serialNavButton, 0),
            (self.ui.functionNavButton, 1),
            (self.ui.settingsNavButton, 2),
        ]
        self.nav_buttons = [button for button, _ in nav_pairs]
        for button, index in nav_pairs:
            button.clicked.connect(lambda checked=False, page_index=index: self._select_page(page_index))

        self.serial_service.data_received.connect(self._handle_received_data)
        self.serial_service.opened.connect(self._handle_opened)
        self.serial_service.closed.connect(self._handle_closed)
        self.serial_service.error.connect(self._show_error)
        self.serial_service.stats_changed.connect(self._update_counts)

        self.serial_page.refresh_ports_requested.connect(self._refresh_ports)
        self.serial_page.open_port_requested.connect(self._open_port)
        self.serial_page.close_port_requested.connect(self._close_port)
        self.serial_page.send_data_requested.connect(self._send_payload)
        self.serial_page.clear_receive_requested.connect(self._clear_receive)
        self.serial_page.save_receive_requested.connect(self._save_receive_data)

        self.function_page.preview_requested.connect(self._preview_function)
        self.function_page.send_requested.connect(self._start_function_send)
        self.function_page.stop_requested.connect(self._stop_function_send)

        self.settings_page.save_requested.connect(self._save_settings)

    def _apply_theme(self):
        app = QApplication.instance()
        if app is not None:
            self.settings.theme = self.theme_service.apply_theme(app, self.settings.theme)
        else:
            self.settings.theme = self.theme_service.apply_theme(self, self.settings.theme)

    def _apply_settings(self):
        self.serial_page.set_default_baudrate(self.settings.default_baudrate)
        self.serial_page.set_default_save_path(self.settings.default_save_path)
        self.settings_page.set_settings(self.settings)
        if self.settings.auto_connect:
            QTimer.singleShot(100, lambda: self._open_port(self.serial_page.serial_config()))

    def _save_settings(self, settings):
        self.settings = settings
        self._apply_theme()
        self.config_service.save_settings(self.settings)
        self.serial_page.set_default_baudrate(self.settings.default_baudrate)
        self.serial_page.set_default_save_path(self.settings.default_save_path)
        self.settings_page.set_settings(self.settings)
        QMessageBox.information(self, "设置", "设置已保存")

    def _select_page(self, index):
        self.ui.pageStack.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setProperty("active", button_index == index)
            button.style().unpolish(button)
            button.style().polish(button)

    def _refresh_ports(self):
        if self.port_scan_thread is not None and self.port_scan_thread.isRunning():
            return
        self.serial_page.set_refreshing(True)
        self.port_scan_thread = PortScanThread(self)
        self.port_scan_thread.ports_ready.connect(self._handle_ports_refreshed)
        self.port_scan_thread.scan_failed.connect(self._show_error)
        self.port_scan_thread.finished.connect(self._finish_port_refresh)
        self.port_scan_thread.start()

    def _handle_ports_refreshed(self, ports):
        self.serial_page.set_ports(ports)

    def _finish_port_refresh(self):
        self.serial_page.set_refreshing(False)
        if self.port_scan_thread is not None:
            self.port_scan_thread.deleteLater()
            self.port_scan_thread = None

    def _open_port(self, config):
        self.current_port = config.port_name or "-"
        self.current_baud = str(config.baud_rate)
        self.serial_service.open_port(config)

    def _close_port(self):
        self.serial_service.close_port()

    def _handle_opened(self):
        self.connected = True
        self.serial_page.set_connected(True)
        self._update_status()

    def _handle_closed(self):
        self.connected = False
        self.serial_page.set_connected(False)
        self._stop_function_send()
        self._update_status()

    def _handle_received_data(self, data):
        self.serial_page.append_received_data(data)

    def _send_payload(self, payload):
        self.serial_service.send_bytes(payload)

    def _clear_receive(self):
        self.serial_service.reset_receive_count()

    def _save_receive_data(self, path):
        try:
            save_text_file(path, self.serial_page.receive_text())
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
        if not self.serial_service.is_open():
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
