# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtSerialPort import QSerialPort
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QWidget

from models.serial_config import ReceiveOptions, SerialConfig
from ui.generated.serial_page_ui import Ui_SerialPage
from utils.format_utils import format_received_data, hex_to_bytes


class SerialPage(QWidget):
    refresh_ports_requested = pyqtSignal()
    open_port_requested = pyqtSignal(object)
    close_port_requested = pyqtSignal()
    send_data_requested = pyqtSignal(bytes)
    clear_receive_requested = pyqtSignal()
    save_receive_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.ui = Ui_SerialPage()
        self.ui.setupUi(self)
        self.default_save_path = ""
        self._ports = []
        self._connected = False
        self._init_options()
        self._connect_signals()

    def _init_options(self):
        self.ui.commTypeComboBox.addItems(["串口"])
        self.ui.baudComboBox.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"])
        self.ui.baudComboBox.setCurrentText("115200")
        self.ui.dataBitsComboBox.addItems(["数据位-5", "数据位-6", "数据位-7", "数据位-8"])
        self.ui.dataBitsComboBox.setCurrentText("数据位-8")
        self.ui.parityComboBox.addItems(["校验位-无", "校验位-奇", "校验位-偶"])
        self.ui.stopBitsComboBox.addItems(["停止位-1", "停止位-1.5", "停止位-2"])
        self.ui.dataFormatComboBox.addItems(["RawData"])
        self.ui.protocolComboBox.addItems(["Test_Protocol2"])
        self.ui.displayModeComboBox.addItems(["UTF-8", "Log"])
        self.ui.sendFormatComboBox.addItems(["ABC", "Text", "HEX"])
        self.ui.checksumComboBox.addItems(["crc8", "none"])
        self.ui.lineEndingComboBox.addItems(["None", "\\n", "\\r\\n"])

    def _connect_signals(self):
        self.ui.refreshButton.clicked.connect(self.refresh_ports_requested)
        self.ui.toggleButton.clicked.connect(self._request_toggle_connection)
        self.ui.sendButton.clicked.connect(self._request_send_data)
        self.ui.clearReceiveButton.clicked.connect(self._request_clear_receive)
        self.ui.saveReceiveButton.clicked.connect(self._select_save_path)
        self.ui.sendLineEdit.returnPressed.connect(self._request_send_data)

    def set_default_baudrate(self, baudrate):
        self.ui.baudComboBox.setCurrentText(str(baudrate))

    def set_default_save_path(self, path):
        self.default_save_path = path or ""

    def set_refreshing(self, refreshing):
        self.ui.refreshButton.setEnabled(not refreshing)
        self.ui.refreshButton.setText("刷新中..." if refreshing else "刷新")

    def set_ports(self, ports):
        current = self.current_port_name()
        self._ports = ports
        self.ui.portComboBox.blockSignals(True)
        self.ui.portComboBox.clear()
        for port in ports:
            label = port["name"]
            if port.get("description"):
                label = f"{port['name']} - {port['description']}"
            self.ui.portComboBox.addItem(label, port["name"])
        self.ui.portComboBox.blockSignals(False)
        if current:
            for index in range(self.ui.portComboBox.count()):
                if self.ui.portComboBox.itemData(index) == current:
                    self.ui.portComboBox.setCurrentIndex(index)
                    break

    def current_port_name(self):
        data = self.ui.portComboBox.currentData()
        if data:
            return str(data).strip()
        return self.ui.portComboBox.currentText().split(" - ", 1)[0].strip()

    def current_baudrate(self):
        return self.ui.baudComboBox.currentText().strip() or "115200"

    def serial_config(self):
        parity_map = {
            "校验位-无": QSerialPort.NoParity,
            "校验位-奇": QSerialPort.OddParity,
            "校验位-偶": QSerialPort.EvenParity,
        }
        data_bits_map = {
            "数据位-5": QSerialPort.Data5,
            "数据位-6": QSerialPort.Data6,
            "数据位-7": QSerialPort.Data7,
            "数据位-8": QSerialPort.Data8,
        }
        stop_bits_map = {
            "停止位-1": QSerialPort.OneStop,
            "停止位-1.5": QSerialPort.OneAndHalfStop,
            "停止位-2": QSerialPort.TwoStop,
        }
        return SerialConfig(
            port_name=self.current_port_name(),
            baud_rate=int(self.current_baudrate()),
            parity=parity_map.get(self.ui.parityComboBox.currentText(), QSerialPort.NoParity),
            data_bits=data_bits_map.get(self.ui.dataBitsComboBox.currentText(), QSerialPort.Data8),
            stop_bits=stop_bits_map.get(self.ui.stopBitsComboBox.currentText(), QSerialPort.OneStop),
            rts=self.ui.rtsCheckBox.isChecked(),
            dtr=self.ui.dtrCheckBox.isChecked(),
        )

    def receive_options(self):
        return ReceiveOptions(
            hex_display=self.ui.hexCheckBox.isChecked(),
            timestamp=self.ui.timestampCheckBox.isChecked(),
            auto_scroll=self.ui.autoScrollCheckBox.isChecked(),
            paused=False,
        )

    def set_connected(self, connected):
        self._connected = connected
        self.ui.toggleButton.setText("断开" if connected else "连接")
        self.ui.toggleButton.setProperty("connected", connected)
        self.ui.toggleButton.style().unpolish(self.ui.toggleButton)
        self.ui.toggleButton.style().polish(self.ui.toggleButton)

    def append_received_data(self, data):
        options = self.receive_options()
        text = format_received_data(data, hex_display=options.hex_display, timestamp=options.timestamp)
        if self.ui.displayModeComboBox.currentText() == "Log" and not text.endswith("\n"):
            text += "\n"
        self._append_receive_text(text)

    def clear_receive_data(self):
        self.ui.receivePlainTextEdit.clear()

    def receive_text(self):
        return self.ui.receivePlainTextEdit.toPlainText()

    def _append_receive_text(self, text):
        cursor = self.ui.receivePlainTextEdit.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.ui.receivePlainTextEdit.setTextCursor(cursor)
        if self.ui.autoScrollCheckBox.isChecked():
            self.ui.receivePlainTextEdit.ensureCursorVisible()

    def _request_toggle_connection(self):
        if self._connected:
            self.close_port_requested.emit()
            return
        self.open_port_requested.emit(self.serial_config())

    def _request_send_data(self):
        text = self.ui.sendLineEdit.text()
        try:
            if self.ui.sendFormatComboBox.currentText() == "HEX":
                payload = hex_to_bytes(text)
            else:
                payload = (text + self._line_ending()).encode("utf-8")
        except ValueError as exc:
            QMessageBox.warning(self, "提示", f"HEX 数据无效: {exc}")
            return
        self.send_data_requested.emit(payload)

    def _line_ending(self):
        ending = self.ui.lineEndingComboBox.currentText()
        if ending == "\\n":
            return "\n"
        if ending == "\\r\\n":
            return "\r\n"
        return ""

    def _request_clear_receive(self):
        self.clear_receive_data()
        self.clear_receive_requested.emit()

    def _select_save_path(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存接收数据",
            self.default_save_path,
            "文本文件 (*.txt);;所有文件 (*)",
        )
        if path:
            self.save_receive_requested.emit(path)
