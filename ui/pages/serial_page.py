# -*- coding: utf-8 -*-
from PyQt5.QtCore import QEvent, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QPainter, QPen, QPixmap, QTextCursor
from PyQt5.QtSerialPort import QSerialPort
from PyQt5.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from models.serial_config import ReceiveOptions, SerialConfig
from ui.generated.serial_page_ui import Ui_SerialPage
from utils.format_utils import bytes_to_hex, bytes_to_hex_keep_newlines, current_timestamp, hex_to_bytes


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
        self._received_chunks = []
        self._connected = False
        self._send_text_guard = False
        self._send_format = "ABC"
        self._continuous_send_count = 0
        self._hex_hint_elapsed = 0

        self._init_resizable_io_area()
        self._init_options()
        self._init_receive_toggle_buttons()
        self._init_send_menu_button()
        self._init_hex_hint_popup()
        self._init_continuous_send_timer()
        self._connect_signals()

    def _init_resizable_io_area(self):
        receive_index = self.ui.pageLayout.indexOf(self.ui.receivePanelFrame)
        self.ui.pageLayout.removeWidget(self.ui.receivePanelFrame)
        self.ui.pageLayout.removeWidget(self.ui.sendBarFrame)

        self.io_splitter = QSplitter(Qt.Vertical, self)
        self.io_splitter.setObjectName("ioSplitter")
        self.io_splitter.setChildrenCollapsible(False)
        self.io_splitter.addWidget(self.ui.receivePanelFrame)
        self.io_splitter.addWidget(self.ui.sendBarFrame)
        self.io_splitter.setStretchFactor(0, 1)
        self.io_splitter.setStretchFactor(1, 0)
        self.io_splitter.setSizes([420, 100])

        self.ui.sendBarFrame.setMaximumHeight(16777215)
        self.ui.sendPlainTextEdit.setMaximumHeight(16777215)
        self.ui.pageLayout.insertWidget(receive_index, self.io_splitter)

    def _init_options(self):
        self.ui.commTypeComboBox.addItems(["串口"])
        self.ui.baudComboBox.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"])
        self.ui.baudComboBox.setCurrentText("115200")
        self.ui.dataBitsComboBox.addItems(["数据位 5", "数据位 6", "数据位 7", "数据位 8"])
        self.ui.dataBitsComboBox.setCurrentText("数据位 8")
        self.ui.parityComboBox.addItems(["校验位 无", "校验位 奇", "校验位 偶"])
        self.ui.stopBitsComboBox.addItems(["停止位 1", "停止位 1.5", "停止位 2"])
        self.ui.dataFormatComboBox.addItems(["RawData"])
        self.ui.protocolComboBox.addItems(["Test_Protocol2"])
        self.ui.displayModeComboBox.addItems(["UTF-8", "Log"])
        self.ui.sendFormatComboBox.addItems(["ABC", "HEX"])
        self._send_format = self.ui.sendFormatComboBox.currentText()
        self.ui.checksumComboBox.addItems(["crc8", "none"])
        self.ui.lineEndingComboBox.addItems(["None", "\\n", "\\r\\n"])
        self.ui.sendPlainTextEdit.setTabChangesFocus(True)

    def _init_receive_toggle_buttons(self):
        self.ui.hexToggleButton.setCheckable(True)
        self.ui.hexToggleButton.toggled.connect(self._update_hex_toggle_text)
        self._update_hex_toggle_text(self.ui.hexToggleButton.isChecked())

        self._timestamp_icons = {
            False: self._clock_icon(Qt.lightGray),
            True: self._clock_icon(Qt.white),
        }
        self.ui.timestampButton.setCheckable(True)
        self.ui.timestampButton.setIcon(self._timestamp_icons[False])
        self.ui.timestampButton.toggled.connect(self._update_timestamp_toggle_icon)
        self.ui.timestampButton.setToolTip("Time Stamp")

        self._auto_scroll_icons = {
            False: self._auto_scroll_icon(Qt.lightGray),
            True: self._auto_scroll_icon(Qt.white),
        }
        self.ui.autoScrollButton.setCheckable(True)
        self.ui.autoScrollButton.setChecked(True)
        self.ui.autoScrollButton.setIcon(self._auto_scroll_icons[True])
        self.ui.autoScrollButton.toggled.connect(self._update_auto_scroll_icon)
        self.ui.autoScrollButton.setToolTip("Auto Scroll")

    def _clock_icon(self, color):
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(3, 3, 12, 12)
        painter.drawLine(9, 9, 9, 5)
        painter.drawLine(9, 9, 12, 11)
        painter.end()
        return QIcon(pixmap)

    def _auto_scroll_icon(self, color):
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(9, 3, 9, 12)
        painter.drawLine(5, 8, 9, 12)
        painter.drawLine(13, 8, 9, 12)
        painter.drawLine(4, 15, 14, 15)
        painter.end()
        return QIcon(pixmap)

    def _update_hex_toggle_text(self, checked):
        self.ui.hexToggleButton.setText("HEX" if checked else "ABC")

    def _update_timestamp_toggle_icon(self, checked):
        self.ui.timestampButton.setIcon(self._timestamp_icons[checked])

    def _update_auto_scroll_icon(self, checked):
        self.ui.autoScrollButton.setIcon(self._auto_scroll_icons[checked])

    def _init_send_menu_button(self):
        original_button = self.ui.sendButton
        self.send_tool_button = QToolButton(self.ui.sendBarFrame)
        self.send_tool_button.setObjectName("sendToolButton")
        self.send_tool_button.setText("Send")
        self.send_tool_button.setPopupMode(QToolButton.MenuButtonPopup)
        self.send_tool_button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.send_tool_button.setSizePolicy(original_button.sizePolicy())

        index = self.ui.sendBarLayout.indexOf(original_button)
        self.ui.sendBarLayout.removeWidget(original_button)
        original_button.hide()
        original_button.deleteLater()
        self.ui.sendButton = self.send_tool_button
        self.ui.sendBarLayout.insertWidget(index, self.send_tool_button)

        self.send_menu = QMenu(self.send_tool_button)
        self.send_menu.setObjectName("sendSettingsMenu")
        self.send_tool_button.setMenu(self.send_menu)
        self._build_send_menu()

    def _build_send_menu(self):
        self.continuous_send_check = QCheckBox("连续发送", self.send_menu)
        self.continuous_send_check.setObjectName("sendMenuCheckBox")
        self.continuous_send_check.toggled.connect(self._handle_continuous_mode_changed)
        self._add_widget_menu_row(self.continuous_send_check)

        self.send_delay_spinbox = self._add_number_menu_row("发送后延时(ms):", 500, 50, 60000, 100)
        self.send_delay_spinbox.valueChanged.connect(self._update_continuous_send_interval)
        self.send_menu.addSeparator()
        self.repeat_count_spinbox = self._add_number_menu_row("重复次数:", -1, -1, 1000000, 1)
        self.send_menu.addSeparator()

        self.enter_send_radio = QRadioButton("按Enter发送", self.send_menu)
        self.enter_send_radio.setObjectName("sendMenuRadioButton")
        self.ctrl_enter_send_radio = QRadioButton("按Ctrl+Enter发送", self.send_menu)
        self.ctrl_enter_send_radio.setObjectName("sendMenuRadioButton")
        self.ctrl_enter_send_radio.setChecked(True)
        self.enter_send_radio.toggled.connect(
            lambda checked: self.ctrl_enter_send_radio.setChecked(False) if checked else None
        )
        self.ctrl_enter_send_radio.toggled.connect(
            lambda checked: self.enter_send_radio.setChecked(False) if checked else None
        )
        self._add_widget_menu_row(self.enter_send_radio)
        self._add_widget_menu_row(self.ctrl_enter_send_radio)

    def _add_widget_menu_row(self, widget):
        action = QWidgetAction(self.send_menu)
        row = QWidget(self.send_menu)
        row.setObjectName("sendMenuRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.addWidget(widget)
        layout.addStretch(1)
        action.setDefaultWidget(row)
        self.send_menu.addAction(action)
        return action

    def _add_number_menu_row(self, label_text, value, minimum, maximum, step):
        action = QWidgetAction(self.send_menu)
        row = QWidget(self.send_menu)
        row.setObjectName("sendMenuRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)

        label = QLabel(label_text, row)
        label.setObjectName("sendMenuLabel")
        layout.addWidget(label)

        minus_button = QPushButton("-", row)
        minus_button.setObjectName("sendMenuStepButton")
        layout.addWidget(minus_button)

        spinbox = QSpinBox(row)
        spinbox.setObjectName("sendMenuSpinBox")
        spinbox.setRange(minimum, maximum)
        spinbox.setSingleStep(step)
        spinbox.setValue(value)
        spinbox.setButtonSymbols(QSpinBox.NoButtons)
        spinbox.setFixedWidth(76)
        layout.addWidget(spinbox)

        plus_button = QPushButton("+", row)
        plus_button.setObjectName("sendMenuStepButton")
        layout.addWidget(plus_button)

        layout.addStretch(1)
        minus_button.clicked.connect(lambda: spinbox.setValue(max(spinbox.minimum(), spinbox.value() - step)))
        plus_button.clicked.connect(lambda: spinbox.setValue(min(spinbox.maximum(), spinbox.value() + step)))

        action.setDefaultWidget(row)
        self.send_menu.addAction(action)
        return spinbox

    def _init_hex_hint_popup(self):
        self.hex_hint_frame = QFrame(self)
        self.hex_hint_frame.setObjectName("hexHintFrame")
        self.hex_hint_frame.setFixedSize(260, 70)
        self.hex_hint_frame.setCursor(Qt.PointingHandCursor)
        self.hex_hint_frame.mousePressEvent = self._hide_hex_hint
        self.hex_hint_frame.hide()

        layout = QVBoxLayout(self.hex_hint_frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        self.hex_hint_label = QLabel("HEX 格式未完成", self.hex_hint_frame)
        self.hex_hint_label.setObjectName("hexHintLabel")
        layout.addWidget(self.hex_hint_label)

        self.hex_hint_progress = QProgressBar(self.hex_hint_frame)
        self.hex_hint_progress.setObjectName("hexHintProgress")
        self.hex_hint_progress.setRange(0, 100)
        self.hex_hint_progress.setValue(0)
        self.hex_hint_progress.setTextVisible(False)
        layout.addWidget(self.hex_hint_progress)

        self.hex_hint_timer = QTimer(self)
        self.hex_hint_timer.setInterval(25)
        self.hex_hint_timer.timeout.connect(self._advance_hex_hint)

    def _init_continuous_send_timer(self):
        self.continuous_send_timer = QTimer(self)
        self.continuous_send_timer.timeout.connect(self._send_next_continuous_payload)

    def _connect_signals(self):
        self.ui.refreshButton.clicked.connect(self.refresh_ports_requested)
        self.ui.toggleButton.clicked.connect(self._request_toggle_connection)
        self.ui.sendButton.clicked.connect(self._handle_send_button_clicked)
        self.ui.clearReceiveButton.clicked.connect(self._request_clear_receive)
        self.ui.saveReceiveButton.clicked.connect(self._select_save_path)
        self.ui.hexToggleButton.toggled.connect(self._render_receive_history)
        self.ui.timestampButton.toggled.connect(self._render_receive_history)
        self.ui.displayModeComboBox.currentTextChanged.connect(self._render_receive_history)
        self.ui.sendFormatComboBox.currentTextChanged.connect(self._handle_send_format_changed)
        self.ui.sendPlainTextEdit.textChanged.connect(self._format_hex_send_text)
        self.ui.sendPlainTextEdit.installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched is self.ui.sendPlainTextEdit and event.type() == QEvent.KeyPress:
            key_is_enter = event.key() in (Qt.Key_Return, Qt.Key_Enter)
            if key_is_enter:
                ctrl_pressed = bool(event.modifiers() & Qt.ControlModifier)
                if self.enter_send_radio.isChecked() and not ctrl_pressed:
                    self._request_send_data()
                    return True
                if self.ctrl_enter_send_radio.isChecked() and ctrl_pressed:
                    self._request_send_data()
                    return True
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "hex_hint_frame") and self.hex_hint_frame.isVisible():
            self._position_hex_hint()

    def closeEvent(self, event):
        self._stop_continuous_send()
        super().closeEvent(event)

    def hideEvent(self, event):
        self._stop_continuous_send()
        super().hideEvent(event)

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
            "校验位 无": QSerialPort.NoParity,
            "校验位 奇": QSerialPort.OddParity,
            "校验位 偶": QSerialPort.EvenParity,
        }
        data_bits_map = {
            "数据位 5": QSerialPort.Data5,
            "数据位 6": QSerialPort.Data6,
            "数据位 7": QSerialPort.Data7,
            "数据位 8": QSerialPort.Data8,
        }
        stop_bits_map = {
            "停止位 1": QSerialPort.OneStop,
            "停止位 1.5": QSerialPort.OneAndHalfStop,
            "停止位 2": QSerialPort.TwoStop,
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
            hex_display=self.ui.hexToggleButton.isChecked(),
            timestamp=self.ui.timestampButton.isChecked(),
            auto_scroll=self.ui.autoScrollButton.isChecked(),
            paused=False,
        )

    def set_connected(self, connected):
        self._connected = connected
        if not connected:
            self._stop_continuous_send()
        self.ui.toggleButton.setText("断开" if connected else "连接")
        self.ui.toggleButton.setProperty("connected", connected)
        self.ui.toggleButton.style().unpolish(self.ui.toggleButton)
        self.ui.toggleButton.style().polish(self.ui.toggleButton)

    def append_received_data(self, data):
        raw_data = bytes(data)
        self._received_chunks.append((raw_data, current_timestamp()))
        text = self._format_received_chunk(raw_data, self._received_chunks[-1][1])
        self._append_receive_text(text)

    def clear_receive_data(self):
        self._received_chunks.clear()
        self.ui.receivePlainTextEdit.clear()

    def receive_text(self):
        return self.ui.receivePlainTextEdit.toPlainText()

    def _append_receive_text(self, text):
        auto_scroll = self.ui.autoScrollButton.isChecked()
        scroll_bar = self.ui.receivePlainTextEdit.verticalScrollBar()
        scroll_position = scroll_bar.value()

        cursor = QTextCursor(self.ui.receivePlainTextEdit.document())
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        if auto_scroll:
            self.ui.receivePlainTextEdit.setTextCursor(cursor)
            self.ui.receivePlainTextEdit.ensureCursorVisible()
        else:
            scroll_bar.setValue(scroll_position)

    def _render_receive_history(self, *_args):
        text = "".join(
            self._format_received_chunk(raw_data, timestamp)
            for raw_data, timestamp in self._received_chunks
        )
        self.ui.receivePlainTextEdit.setPlainText(text)
        if self.ui.autoScrollButton.isChecked():
            cursor = self.ui.receivePlainTextEdit.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.ui.receivePlainTextEdit.setTextCursor(cursor)
            self.ui.receivePlainTextEdit.ensureCursorVisible()

    def _format_received_chunk(self, data, timestamp):
        if self.ui.hexToggleButton.isChecked():
            text = bytes_to_hex_keep_newlines(data)
        else:
            text = bytes(data).decode("utf-8", errors="ignore")
        if self.ui.timestampButton.isChecked():
            text = timestamp + text
        if self.ui.displayModeComboBox.currentText() == "Log" and not text.endswith("\n"):
            text += "\n"
        return text

    def _request_toggle_connection(self):
        if self._connected:
            self.close_port_requested.emit()
            return
        self.open_port_requested.emit(self.serial_config())

    def _request_send_data(self):
        text = self.ui.sendPlainTextEdit.toPlainText()
        try:
            if self.ui.sendFormatComboBox.currentText() == "HEX":
                cleaned = self._hex_digits(text)
                if len(cleaned) % 2:
                    self._show_hex_incomplete_hint()
                    return False
                payload = hex_to_bytes(cleaned) + self._line_ending().encode("utf-8")
            else:
                payload = (text + self._line_ending()).encode("utf-8")
        except ValueError as exc:
            self._show_hex_incomplete_hint(str(exc))
            return False
        self.send_data_requested.emit(payload)
        return True

    def _handle_send_button_clicked(self):
        if self.continuous_send_timer.isActive():
            self._stop_continuous_send()
            return
        if self.continuous_send_check.isChecked():
            self._start_continuous_send()
            return
        self._request_send_data()

    def _handle_continuous_mode_changed(self, checked):
        if not checked:
            self._stop_continuous_send()
        self._update_send_button_text()

    def _start_continuous_send(self):
        if not self._connected:
            self._show_hex_incomplete_hint("请先打开串口")
            self._update_continuous_send_state(False)
            return
        if not self._has_send_content():
            self._show_hex_incomplete_hint("发送内容为空")
            self._update_continuous_send_state(False)
            return

        self._continuous_send_count = 0
        self.continuous_send_timer.start(self.send_delay_spinbox.value())
        self._update_continuous_send_state(True)
        self._send_next_continuous_payload()

    def _send_next_continuous_payload(self):
        repeat_count = self.repeat_count_spinbox.value()
        if repeat_count >= 0 and self._continuous_send_count >= repeat_count:
            self._stop_continuous_send()
            return
        if not self._request_send_data():
            self._stop_continuous_send()
            return
        self._continuous_send_count += 1
        if repeat_count >= 0 and self._continuous_send_count >= repeat_count:
            self._stop_continuous_send()

    def _update_continuous_send_interval(self, interval):
        if self.continuous_send_timer.isActive():
            self.continuous_send_timer.setInterval(interval)

    def _stop_continuous_send(self):
        self.continuous_send_timer.stop()
        self._update_continuous_send_state(False)

    def _update_continuous_send_state(self, active):
        self.continuous_send_check.setText("● 连续发送" if active else "连续发送")
        self._update_send_button_text()

    def _update_send_button_text(self):
        if self.continuous_send_timer.isActive():
            self.ui.sendButton.setText("终止")
        elif self.continuous_send_check.isChecked():
            self.ui.sendButton.setText("连续发送")
        else:
            self.ui.sendButton.setText("Send")

    def _has_send_content(self):
        text = self.ui.sendPlainTextEdit.toPlainText()
        if self.ui.sendFormatComboBox.currentText() == "HEX":
            return bool(self._hex_digits(text))
        return bool(text)

    def _handle_send_format_changed(self, format_text):
        if self._send_text_guard or format_text == self._send_format:
            self._send_format = format_text
            return

        text = self.ui.sendPlainTextEdit.toPlainText()
        if format_text == "HEX":
            converted = bytes_to_hex(text.encode("utf-8"))
            self._set_send_text(converted)
        elif self._send_format == "HEX":
            cleaned = self._hex_digits(text)
            if len(cleaned) % 2:
                self._show_hex_incomplete_hint()
                self._set_send_format("HEX")
                return
            decoded = hex_to_bytes(cleaned).decode("utf-8", errors="replace")
            self._set_send_text(decoded)

        self._send_format = format_text

    def _format_hex_send_text(self):
        if self._send_text_guard or self.ui.sendFormatComboBox.currentText() != "HEX":
            return

        text = self.ui.sendPlainTextEdit.toPlainText()
        cursor = self.ui.sendPlainTextEdit.textCursor()
        digit_count = len(self._hex_digits(text[:cursor.position()]))
        digits = self._hex_digits(text)
        formatted = self._format_hex_digits(digits)
        if text == formatted:
            return

        self._send_text_guard = True
        self.ui.sendPlainTextEdit.setPlainText(formatted)
        cursor = self.ui.sendPlainTextEdit.textCursor()
        cursor.setPosition(self._cursor_position_for_hex_digit_count(formatted, digit_count))
        self.ui.sendPlainTextEdit.setTextCursor(cursor)
        self._send_text_guard = False

    def _set_send_text(self, text):
        self._send_text_guard = True
        self.ui.sendPlainTextEdit.setPlainText(text)
        cursor = self.ui.sendPlainTextEdit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.ui.sendPlainTextEdit.setTextCursor(cursor)
        self._send_text_guard = False

    def _set_send_format(self, format_text):
        self._send_text_guard = True
        self.ui.sendFormatComboBox.setCurrentText(format_text)
        self._send_text_guard = False
        self._send_format = format_text

    def _hex_digits(self, text):
        return "".join(char for char in text.upper() if char in "0123456789ABCDEF")

    def _format_hex_digits(self, digits):
        return " ".join(digits[index:index + 2] for index in range(0, len(digits), 2))

    def _cursor_position_for_hex_digit_count(self, text, digit_count):
        if digit_count <= 0:
            return 0
        seen = 0
        for index, char in enumerate(text):
            if char != " ":
                seen += 1
                if seen == digit_count:
                    return index + 1
        return len(text)

    def _show_hex_incomplete_hint(self, message="HEX 格式未完成"):
        self.hex_hint_label.setText(message)
        self._hex_hint_elapsed = 0
        self.hex_hint_progress.setValue(0)
        self._position_hex_hint()
        self.hex_hint_frame.show()
        self.hex_hint_frame.raise_()
        self.hex_hint_timer.start()

    def _advance_hex_hint(self):
        duration = 1800
        self._hex_hint_elapsed += self.hex_hint_timer.interval()
        progress = min(100, int(self._hex_hint_elapsed * 100 / duration))
        self.hex_hint_progress.setValue(progress)
        if progress >= 100:
            self._hide_hex_hint()

    def _hide_hex_hint(self, *_args):
        self.hex_hint_timer.stop()
        self.hex_hint_frame.hide()

    def _position_hex_hint(self):
        margin = 18
        x = max(margin, self.width() - self.hex_hint_frame.width() - margin)
        y = max(margin, self.height() - self.hex_hint_frame.height() - self.ui.sendBarFrame.height() - margin)
        self.hex_hint_frame.move(x, y)

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
