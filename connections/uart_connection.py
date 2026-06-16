# -*- coding: utf-8 -*-
from PyQt5.QtCore import QObject, QByteArray, pyqtSignal

from connections.base_connection import BaseConnection
from services.serial_service import SerialService


class UartConnection(QObject, BaseConnection):
    data_received = pyqtSignal(QByteArray)
    opened = pyqtSignal()
    closed = pyqtSignal()
    error = pyqtSignal(str)
    stats_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = SerialService()
        self.service.data_received.connect(self.data_received)
        self.service.opened.connect(self.opened)
        self.service.closed.connect(self.closed)
        self.service.error.connect(self.error)
        self.service.stats_changed.connect(self.stats_changed)

    def connect(self, config=None):
        return self.service.open_port(config)

    def disconnect(self):
        self.service.close_port()

    def send(self, data):
        return self.service.send_bytes(data)

    def receive(self):
        return None

    def is_open(self):
        return self.service.is_open()

    def reset_receive_count(self):
        self.service.reset_receive_count()
