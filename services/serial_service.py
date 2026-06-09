# -*- coding: utf-8 -*-
from PyQt5.QtCore import QObject, QByteArray, QIODevice, pyqtSignal
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo


class SerialService(QObject):
    data_received = pyqtSignal(QByteArray)
    opened = pyqtSignal()
    closed = pyqtSignal()
    error = pyqtSignal(str)
    stats_changed = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.serial = QSerialPort()
        self.receive_count = 0
        self.send_count = 0

        self.serial.readyRead.connect(self._read_data)
        self.serial.errorOccurred.connect(self._handle_error)

    @staticmethod
    def list_ports():
        ports = []
        for port in QSerialPortInfo.availablePorts():
            ports.append(
                {
                    "name": port.portName(),
                    "description": port.description() or "",
                    "manufacturer": port.manufacturer() or "",
                    "serial_number": port.serialNumber() or "",
                    "location": port.systemLocation(),
                    "vendor_id": f"0x{port.vendorIdentifier():04x}" if port.vendorIdentifier() else "",
                    "product_id": f"0x{port.productIdentifier():04x}" if port.productIdentifier() else "",
                    "is_busy": port.isBusy(),
                }
            )
        return ports

    def is_open(self):
        return self.serial.isOpen()

    def open_port(self, config):
        if not config.port_name:
            self.error.emit("请选择串口")
            return False

        if self.serial.isOpen():
            self.serial.close()

        self.serial.setPortName(config.port_name)
        self.serial.setBaudRate(config.baud_rate)
        self.serial.setParity(config.parity)
        self.serial.setDataBits(config.data_bits)
        self.serial.setStopBits(config.stop_bits)
        self.serial.setFlowControl(QSerialPort.NoFlowControl)

        if not self.serial.open(QIODevice.ReadWrite):
            self.error.emit(f"无法打开串口 {config.port_name}: {self.serial.errorString()}")
            return False

        self.serial.setRequestToSend(config.rts)
        self.serial.setDataTerminalReady(config.dtr)
        self.opened.emit()
        self.stats_changed.emit(self.receive_count, self.send_count)
        return True

    def close_port(self):
        if self.serial.isOpen():
            self.serial.close()
        self.closed.emit()
        self.stats_changed.emit(self.receive_count, self.send_count)

    def send_bytes(self, data):
        if not self.serial.isOpen():
            self.error.emit("串口未打开")
            return False
        if not data:
            self.error.emit("发送数据为空")
            return False

        written = self.serial.write(data)
        if written < 0:
            self.error.emit(f"发送失败: {self.serial.errorString()}")
            return False

        self.serial.flush()
        self.send_count += written
        self.stats_changed.emit(self.receive_count, self.send_count)
        return True

    def reset_receive_count(self):
        self.receive_count = 0
        self.stats_changed.emit(self.receive_count, self.send_count)

    def _read_data(self):
        data = self.serial.readAll()
        if not data:
            return
        self.receive_count += data.size()
        self.data_received.emit(data)
        self.stats_changed.emit(self.receive_count, self.send_count)

    def _handle_error(self, error):
        if error == QSerialPort.NoError:
            return
        if error in (QSerialPort.ResourceError, QSerialPort.PermissionError):
            self.error.emit(self.serial.errorString())
            self.close_port()
