# -*- coding: utf-8 -*-
from PyQt5.QtCore import QThread, pyqtSignal

from services.serial_service import SerialService


class PortScanThread(QThread):
    ports_ready = pyqtSignal(list)
    scan_failed = pyqtSignal(str)

    def run(self):
        try:
            self.ports_ready.emit(SerialService.list_ports(include_busy=False))
        except Exception as exc:
            self.scan_failed.emit(str(exc))
