# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtSerialPort import QSerialPort
from PyQt5.QtWidgets import QWidget

from models.serial_config import SerialConfig
from ui.generated.connection_page_ui import Ui_ConnectionPage


class ConnectionPage(QWidget):
    refresh_requested = pyqtSignal()
    toggle_connection_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ui = Ui_ConnectionPage()
        self.ui.setupUi(self)
        self._ports = []
        self._init_options()
        self.ui.refreshButton.clicked.connect(self.refresh_requested)
        self.ui.toggleButton.clicked.connect(self.toggle_connection_requested)
        self.ui.portComboBox.currentIndexChanged.connect(self.update_port_info)

    def _init_options(self):
        self.ui.baudComboBox.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"])
        self.ui.baudComboBox.setCurrentText("115200")
        self.ui.parityComboBox.addItems(["无校验", "奇校验", "偶校验"])
        self.ui.dataBitsComboBox.addItems(["5", "6", "7", "8"])
        self.ui.dataBitsComboBox.setCurrentText("8")
        self.ui.stopBitsComboBox.addItems(["1", "1.5", "2"])

    def set_default_baudrate(self, baudrate):
        self.ui.baudComboBox.setCurrentText(str(baudrate))

    def set_ports(self, ports):
        current = self.current_port_name()
        self._ports = ports
        self.ui.portComboBox.blockSignals(True)
        self.ui.portComboBox.clear()
        for port in ports:
            self.ui.portComboBox.addItem(port["name"])
        self.ui.portComboBox.blockSignals(False)
        if current:
            index = self.ui.portComboBox.findText(current)
            if index >= 0:
                self.ui.portComboBox.setCurrentIndex(index)
        self.update_port_info()

    def current_port_name(self):
        return self.ui.portComboBox.currentText().strip()

    def get_config(self):
        parity_map = {"无校验": QSerialPort.NoParity, "奇校验": QSerialPort.OddParity, "偶校验": QSerialPort.EvenParity}
        data_bits_map = {"5": QSerialPort.Data5, "6": QSerialPort.Data6, "7": QSerialPort.Data7, "8": QSerialPort.Data8}
        stop_bits_map = {"1": QSerialPort.OneStop, "1.5": QSerialPort.OneAndHalfStop, "2": QSerialPort.TwoStop}
        return SerialConfig(
            port_name=self.current_port_name(),
            baud_rate=int(self.ui.baudComboBox.currentText() or "115200"),
            parity=parity_map.get(self.ui.parityComboBox.currentText(), QSerialPort.NoParity),
            data_bits=data_bits_map.get(self.ui.dataBitsComboBox.currentText(), QSerialPort.Data8),
            stop_bits=stop_bits_map.get(self.ui.stopBitsComboBox.currentText(), QSerialPort.OneStop),
            rts=self.ui.rtsCheckBox.isChecked(),
            dtr=self.ui.dtrCheckBox.isChecked(),
        )

    def set_connected(self, connected):
        self.ui.toggleButton.setText("关闭串口" if connected else "打开串口")

    def update_port_info(self):
        port_name = self.current_port_name()
        port = next((item for item in self._ports if item["name"] == port_name), None)
        if not port:
            self.ui.infoTextEdit.setPlainText("未检测到可用串口")
            return
        self.ui.infoTextEdit.setPlainText(
            "\n".join(
                [
                    f"设备: {port['name']}",
                    f"描述: {port['description'] or '-'}",
                    f"制造商: {port['manufacturer'] or '-'}",
                    f"序列号: {port['serial_number'] or '-'}",
                    f"路径: {port['location'] or '-'}",
                    f"VID: {port['vendor_id'] or '-'}",
                    f"PID: {port['product_id'] or '-'}",
                    f"占用: {'是' if port['is_busy'] else '否'}",
                ]
            )
        )
