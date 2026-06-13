# -*- coding: utf-8 -*-
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from connections.uart_connection import UartConnection
from services.port_scan_thread import PortScanThread
from utils.file_utils import save_text_file


class UartController(QObject):
    status_changed = pyqtSignal(str, str, bool)
    stats_changed = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, widget, connection=None, parent=None):
        super().__init__(parent)
        self.widget = widget
        self.connection = connection or UartConnection(self)
        self.current_port = "-"
        self.current_baud = "-"
        self.connected = False
        self.port_scan_thread = None

        self._connect_connection_signals()
        self._connect_widget_signals()

    def _connect_connection_signals(self):
        self.connection.data_received.connect(self._handle_received_data)
        self.connection.opened.connect(self._handle_opened)
        self.connection.closed.connect(self._handle_closed)
        self.connection.error.connect(self.error)
        self.connection.stats_changed.connect(self.stats_changed)

    def _connect_widget_signals(self):
        self.widget.refresh_ports_requested.connect(self.refresh_ports)
        self.widget.open_port_requested.connect(self.open_port)
        self.widget.close_port_requested.connect(self.close_port)
        self.widget.send_data_requested.connect(self.send)
        self.widget.clear_receive_requested.connect(self.clear_receive)
        self.widget.save_receive_requested.connect(self.save_receive_data)

    def apply_defaults(self, baudrate, save_path):
        self.widget.set_default_baudrate(baudrate)
        self.widget.set_default_save_path(save_path)

    def refresh_ports(self):
        if self.port_scan_thread is not None and self.port_scan_thread.isRunning():
            return
        self.widget.set_refreshing(True)
        self.port_scan_thread = PortScanThread(self)
        self.port_scan_thread.ports_ready.connect(self.widget.set_ports)
        self.port_scan_thread.scan_failed.connect(self.error)
        self.port_scan_thread.finished.connect(self._finish_port_refresh)
        self.port_scan_thread.start()

    def _finish_port_refresh(self):
        self.widget.set_refreshing(False)
        if self.port_scan_thread is not None:
            self.port_scan_thread.deleteLater()
            self.port_scan_thread = None

    def open_port(self, config):
        self.current_port = config.port_name or "-"
        self.current_baud = str(config.baud_rate)
        self.connection.connect(config)

    def close_port(self):
        self.connection.disconnect()

    def send(self, payload):
        return self.connection.send(payload)

    def clear_receive(self):
        self.connection.reset_receive_count()

    def save_receive_data(self, path):
        try:
            save_text_file(path, self.widget.receive_text())
        except OSError as exc:
            self.error.emit(f"Save receive data failed: {exc}")

    def is_open(self):
        return self.connection.is_open()

    def serial_config(self):
        return self.widget.serial_config()

    def auto_connect(self):
        QTimer.singleShot(100, lambda: self.open_port(self.serial_config()))

    def _handle_opened(self):
        self.connected = True
        self.widget.set_connected(True)
        self.status_changed.emit(self.current_port, self.current_baud, self.connected)

    def _handle_closed(self):
        self.connected = False
        self.widget.set_connected(False)
        self.status_changed.emit(self.current_port, self.current_baud, self.connected)

    def _handle_received_data(self, data):
        self.widget.append_received_data(data)
