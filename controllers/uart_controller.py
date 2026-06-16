# -*- coding: utf-8 -*-
from PyQt5.QtCore import QObject, pyqtSignal

from services.just_float_parser import JustFloatParser
from services.serial_service import SerialService


class UartController(QObject):
    status_changed = pyqtSignal(str, str, bool)
    stats_changed = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, widget, connection=None, channel_manager=None, parent=None):
        super().__init__(parent)
        self.widget = widget
        self.connection = connection
        self.channel_manager = channel_manager
        self.service = SerialService()
        self.just_float_parser = JustFloatParser()
        self._open_port_config = None

        self._connect_signals()

    def _connect_signals(self):
        self.widget.refresh_ports_requested.connect(self.refresh_ports)
        self.widget.open_port_requested.connect(self.open_port)
        self.widget.close_port_requested.connect(self.close_port)
        self.widget.send_data_requested.connect(self.send_bytes)
        self.widget.clear_receive_requested.connect(self.clear_receive_data)
        self.widget.save_receive_requested.connect(self.save_receive_data)

        self.service.data_received.connect(self._handle_received_data)
        self.service.opened.connect(self._handle_opened)
        self.service.closed.connect(self._handle_closed)
        self.service.error.connect(self.error)
        self.service.stats_changed.connect(self._handle_stats_changed)

    def is_open(self):
        return self.service.is_open()

    def refresh_ports(self):
        self.widget.set_refreshing(True)
        try:
            ports = self.service.list_ports()
            self.widget.set_ports(ports)
        finally:
            self.widget.set_refreshing(False)

    def auto_connect(self):
        if self.is_open():
            return
        config = self.widget.serial_config()
        self.open_port(config)

    def open_port(self, config):
        self._open_port_config = config
        self.service.open_port(config)

    def close_port(self):
        self.service.close_port()

    def send_bytes(self, data):
        return self.service.send_bytes(data)

    def send(self, data):
        return self.send_bytes(data)

    def clear_receive_data(self):
        self.widget.clear_receive_data()
        self.service.reset_receive_count()

    def save_receive_data(self, path):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.widget.receive_text())

    def _handle_opened(self):
        config = self._open_port_config or self.widget.serial_config()
        self.widget.set_connected(True)
        self.status_changed.emit(config.port_name, str(config.baud_rate), True)

    def _handle_closed(self):
        self.widget.set_connected(False)
        self.status_changed.emit("-", "-", False)

    def _handle_stats_changed(self, receive_count, send_count):
        self.stats_changed.emit(receive_count, send_count)

    def _handle_received_data(self, data):
        raw = bytes(data)
        self.widget.append_received_data(raw)
        if hasattr(self.widget, "current_data_format") and self.widget.current_data_format() == "JustFloat":
            for frame_values in self.just_float_parser.feed(raw):
                if self.channel_manager is not None:
                    sample_interval_s = None
                    if hasattr(self.widget, "plot_period_s"):
                        sample_interval_s = self.widget.plot_period_s()
                    self.channel_manager.update_values(frame_values, sample_interval_s=sample_interval_s)
