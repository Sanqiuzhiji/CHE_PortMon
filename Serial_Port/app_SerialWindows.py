# -*- coding: utf-8 -*-
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QFileDialog
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo

from Serial_Port.Serial_MainWindow import Ui_Serial_MainWindow
from Serial_Port.config_manager import JSONConfigManager
from Serial_Port.app_SerialProcess import SerialProcess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from WindowManager import WindowManagerClass


class SerialAppClass(QMainWindow):
    def __init__(self, window_manager: 'WindowManagerClass'):
        super().__init__()
        self.last_port_list = []
        self.window_manager: WindowManagerClass = window_manager

        # 设置UI界面
        self.ui = Ui_Serial_MainWindow()
        self.ui.setupUi(self)

        # 获取窗口的实际尺寸
        self.design_size = (self.width(), self.height())

        # 初始化JSON配置管理器
        self.config_manager = JSONConfigManager()

        # 初始化串口处理类
        self.serial_process = SerialProcess()

        # 初始化界面
        self.init_serial_ui()

        # 加载上次的设置
        self.load_last_settings()

        # 初始化端口列表
        self.refresh_ports()

        # 设置定时器，每2秒检查一次
        self.port_infor_timer: QTimer = QTimer()
        self.port_infor_timer.timeout.connect(self.refresh_ports)
        self.port_infor_timer.start(1000)

        self.connect_signals()

    def init_serial_ui(self):
        """初始化串口界面"""
        # 初始化波特率组合框
        self.init_baudrate_comboBox()

        # 初始化其他组合框
        self.init_parity_comboBox()
        self.init_databits_comboBox()
        self.init_stopbits_comboBox()

        # 设置组合框为可编辑，允许用户输入
        self.ui.baudrate_cb.setEditable(True)
        self.ui.baudrate_cb.editTextChanged.connect(self.on_baudrate_input)

        # 设置接收和发送文本框
        self.setup_text_edits()

    def setup_text_edits(self):
        """设置接收和发送文本框"""
        # 接收文本框
        self.ui.receive_tEdit.setReadOnly(True)
        self.ui.receive_tEdit.setWordWrapMode(True)
        self.ui.receive_tEdit.setFont(QFont("Consolas", 10))

        # 发送文本框
        self.ui.send_tEdit.setFont(QFont("Consolas", 10))

        # 端口信息文本框
        self.ui.port_info_lEdit.setReadOnly(True)
        self.ui.port_info_lEdit.setPlainText("请选择串口端口")

    def connect_signals(self):
        """连接信号和槽"""
        # 串口处理类信号
        self.serial_process.data_received.connect(self.on_data_received)
        self.serial_process.port_opened.connect(self.on_port_opened)
        self.serial_process.port_closed.connect(self.on_port_closed)
        self.serial_process.error_occurred.connect(self.on_serial_error)

        # 按钮信号
        self.ui.open_btn.clicked.connect(self.toggle_serial_port)
        self.ui.self_clearReceive_btn.clicked.connect(self.clear_receive_data)
        self.ui.pause_Receive_btn.clicked.connect(self.toggle_pause_receive)
        self.ui.save_Receive_btn.clicked.connect(self.save_receive_data)
        self.ui.path_receive_btn.clicked.connect(self.select_receive_path)
        self.ui.self_Send_btn.clicked.connect(self.send_data)
        self.ui.clear_Send_btn.clicked.connect(self.clear_send_data)
        self.ui.path_send_btn.clicked.connect(self.select_send_file)
        self.ui.sendFile_btn.clicked.connect(self.send_file)

        # 复选框信号
        self.ui.hex_receive_chb.stateChanged.connect(self.on_hex_receive_changed)
        self.ui.hex_send_chb.stateChanged.connect(self.on_hex_send_changed)
        self.ui.timestamp_chb.stateChanged.connect(self.on_timestamp_changed)
        self.ui.rts_chb.stateChanged.connect(self.on_flow_control_changed)
        self.ui.dtr_chb.stateChanged.connect(self.on_flow_control_changed)

        # 端口选择变化信号
        self.ui.port_cb.currentIndexChanged.connect(self.update_port_info)

    def toggle_serial_port(self):
        """打开/关闭串口"""
        if self.serial_process.is_open:
            # 关闭串口
            self.serial_process.close_port()
            self.ui.open_btn.setText("打开串口")
        else:
            # 打开串口
            if self.open_serial_port():
                self.ui.open_btn.setText("关闭串口")

    def open_serial_port(self):
        """打开串口"""
        # 获取串口参数
        port_name = self.ui.port_cb.currentText()
        if not port_name or port_name == "未检测到串口":
            QMessageBox.warning(self, "错误", "请选择有效的串口")
            return False

        try:
            baud_rate = int(self.ui.baudrate_cb.currentText())
            data_bits = self.get_databits_value()
            parity = self.get_parity_value()
            stop_bits = self.get_stopbits_value()
            flow_control = QSerialPort.FlowControl.NoFlowControl  # 默认无流控制

            # 打开串口
            if self.serial_process.open_port(port_name, baud_rate, data_bits, parity, stop_bits, flow_control):
                # 保存当前设置
                self.save_current_settings()
                return True
            return False

        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开串口失败: {e}")
            return False

    def save_current_settings(self):
        """保存当前设置"""
        current_settings = {
            "last_port": self.ui.port_cb.currentText(),
            "last_baudrate": self.ui.baudrate_cb.currentText(),
            "last_parity": self.ui.parity_cb.currentText(),
            "last_databits": self.ui.databits_cb.currentText(),
            "last_stopbits": self.ui.stopbits_cb.currentText()
        }
        self.config_manager.save_user_settings(current_settings)

    def get_databits_value(self):
        """获取数据位数值"""
        databits_map = {
            "5": QSerialPort.DataBits.Data5,
            "6": QSerialPort.DataBits.Data6,
            "7": QSerialPort.DataBits.Data7,
            "8": QSerialPort.DataBits.Data8
        }
        current_text = self.ui.databits_cb.currentText()
        return databits_map.get(current_text, QSerialPort.DataBits.Data8)

    def get_parity_value(self):
        """获取校验位数值"""
        parity_map = {
            "无": QSerialPort.Parity.NoParity,
            "奇校验": QSerialPort.Parity.OddParity,
            "偶校验": QSerialPort.Parity.EvenParity
        }
        current_text = self.ui.parity_cb.currentText()
        return parity_map.get(current_text, QSerialPort.Parity.NoParity)

    def get_stopbits_value(self):
        """获取停止位数值"""
        stopbits_map = {
            "1": QSerialPort.StopBits.OneStop,
            "1.5": QSerialPort.StopBits.OneAndHalfStop,
            "2": QSerialPort.StopBits.TwoStop
        }
        current_text = self.ui.stopbits_cb.currentText()
        return stopbits_map.get(current_text, QSerialPort.StopBits.OneStop)

    def on_data_received(self, data):
        """处理接收到的数据"""
        if self.ui.hex_receive_chb.isChecked():
            # 十六进制显示
            hex_data = data.toHex().data().decode()
            formatted_hex = ' '.join([hex_data[i:i + 2] for i in range(0, len(hex_data), 2)])
            display_text = formatted_hex
        else:
            # 文本显示
            display_text = data.data().decode('utf-8', errors='ignore')

        # 添加时间戳
        if self.ui.timestamp_chb.isChecked():
            from datetime import datetime
            timestamp = datetime.now().strftime("[%H:%M:%S] ")
            display_text = timestamp + display_text

        # 追加到接收文本框
        self.append_to_receive(display_text)

        # 自动清空
        if self.ui.auto_clearReceive_chb.isChecked():
            # 这里可以添加自动清空的逻辑，比如达到一定行数后清空
            pass

    def append_to_receive(self, text):
        """将文本追加到接收文本框"""
        cursor = self.ui.receive_tEdit.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.ui.receive_tEdit.setTextCursor(cursor)
        self.ui.receive_tEdit.ensureCursorVisible()

    def send_data(self):
        """发送数据"""
        send_text = self.ui.send_tEdit.toPlainText()
        if not send_text.strip():
            QMessageBox.information(self, "提示", "请输入要发送的数据")
            return

        is_hex = self.ui.hex_send_chb.isChecked()
        if self.serial_process.send_data(send_text, is_hex):
            # 发送成功，可选自动清空
            if self.ui.auto_send_chb.isChecked():
                self.ui.send_tEdit.clear()

    def send_file(self):
        """发送文件"""
        file_path = self.ui.file_send_lEdit.text()
        if not file_path:
            QMessageBox.information(self, "提示", "请先选择要发送的文件")
            return

        if self.serial_process.send_file(file_path):
            QMessageBox.information(self, "成功", "文件发送完成")

    def clear_receive_data(self):
        """清空接收数据"""
        self.ui.receive_tEdit.clear()
        self.serial_process.reset_stats()

    def clear_send_data(self):
        """清空发送数据"""
        self.ui.send_tEdit.clear()

    def toggle_pause_receive(self):
        """暂停/恢复接收"""
        if self.ui.pause_Receive_btn.text() == "暂停接收":
            self.serial_process.pause_receive(True)
            self.ui.pause_Receive_btn.setText("恢复接收")
        else:
            self.serial_process.pause_receive(False)
            self.ui.pause_Receive_btn.setText("暂停接收")

    def save_receive_data(self):
        """保存接收数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存接收数据", "", "文本文件 (*.txt);;所有文件 (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.ui.receive_tEdit.toPlainText())
                QMessageBox.information(self, "成功", "数据已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def select_receive_path(self):
        """选择接收数据保存路径"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "设置接收数据保存路径", "", "文本文件 (*.txt)"
        )

        if file_path:
            self.ui.file_receive_lEdit.setText(file_path)

    def select_send_file(self):
        """选择发送文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择要发送的文件", "", "所有文件 (*)"
        )

        if file_path:
            self.ui.file_send_lEdit.setText(file_path)

    def on_hex_receive_changed(self, state):
        """十六进制接收显示切换"""
        # 可以在这里添加切换显示模式的逻辑
        pass

    def on_hex_send_changed(self, state):
        """十六进制发送切换"""
        pass

    def on_timestamp_changed(self, state):
        """时间戳显示切换"""
        pass

    def on_flow_control_changed(self, state):
        """流控制设置改变"""
        if self.serial_process.is_open:
            rts_state = self.ui.rts_chb.isChecked()
            dtr_state = self.ui.dtr_chb.isChecked()
            self.serial_process.set_flow_control(rts_state, dtr_state)

    def on_port_opened(self):
        """串口打开成功"""
        self.ui.statusbar.showMessage("串口已打开", 3000)

    def on_port_closed(self):
        """串口关闭"""
        self.ui.statusbar.showMessage("串口已关闭", 3000)

    def on_serial_error(self, error_msg):
        """串口错误处理"""
        QMessageBox.critical(self, "串口错误", error_msg)
        self.ui.open_btn.setText("打开串口")

    def init_baudrate_comboBox(self):
        """初始化波特率下拉框"""
        self.ui.baudrate_cb.clear()

        baudrates = self.config_manager.get_config_options("baudrates")
        for item in baudrates:
            self.ui.baudrate_cb.addItem(item["text"], item["value"])

    def init_parity_comboBox(self):
        """初始化校验位下拉框"""
        self.ui.parity_cb.clear()

        parities = self.config_manager.get_config_options("parities")
        for item in parities:
            self.ui.parity_cb.addItem(item["text"], item["value"])

    def init_databits_comboBox(self):
        """初始化数据位下拉框"""
        self.ui.databits_cb.clear()

        databits = self.config_manager.get_config_options("databits")
        for item in databits:
            self.ui.databits_cb.addItem(item["text"], item["value"])

    def init_stopbits_comboBox(self):
        """初始化停止位下拉框"""
        self.ui.stopbits_cb.clear()

        stopbits = self.config_manager.get_config_options("stopbits")
        for item in stopbits:
            self.ui.stopbits_cb.addItem(item["text"], item["value"])

    def on_baudrate_input(self, text):
        """当用户在波特率框中输入时"""
        if text.strip():  # 非空输入
            try:
                baudrate = int(text)
            # 可以在这里添加验证逻辑
            # print(baudrate)
            except ValueError:
                pass  # 输入的不是数字

    def on_open_clicked(self):
        """打开串口按钮点击事件"""
        # 获取当前设置
        current_settings = {
            "last_port": self.ui.port_cb.currentText(),
            "last_baudrate": self.ui.baudrate_cb.currentData(),
            "last_parity": self.ui.parity_cb.currentData(),
            "last_databits": self.ui.databits_cb.currentData(),
            "last_stopbits": self.ui.stopbits_cb.currentData()
        }

        # 保存设置
        self.config_manager.save_user_settings(current_settings)

        # 检查是否是新的波特率
        current_baudrate = self.ui.baudrate_cb.currentText()
        try:
            baud_value = int(current_baudrate)
            # 如果不在预设列表中，添加到自定义
            existing_baudrates = [item["value"] for item in self.config_manager.get_config_options("baudrates")]
            if baud_value not in existing_baudrates:
                self.config_manager.add_custom_option("baudrates", baud_value, current_baudrate)
                # 刷新下拉框显示新选项
                self.init_baudrate_comboBox()
                self.ui.baudrate_cb.setCurrentText(current_baudrate)
        except ValueError:
            pass

        # 打开串口的代码...
        print("打开串口:", current_settings)

    def load_last_settings(self):
        """加载上次的设置"""
        last_settings = self.config_manager.load_user_settings()

        # 设置到界面
        self.ui.port_cb.setCurrentText(last_settings.get("last_port", "COM1"))

        # 设置波特率（需要检查是否存在）
        last_baudrate = last_settings.get("last_baudrate", 115200)
        index = self.ui.baudrate_cb.findData(last_baudrate)
        if index >= 0:
            self.ui.baudrate_cb.setCurrentIndex(index)
        else:
            self.ui.baudrate_cb.setCurrentText(str(last_baudrate))

        # 设置其他参数...
        self.set_comboBox_currentData(self.ui.parity_cb, last_settings.get("last_parity", "N"))
        self.set_comboBox_currentData(self.ui.databits_cb, last_settings.get("last_databits", 8))
        self.set_comboBox_currentData(self.ui.stopbits_cb, last_settings.get("last_stopbits", 1))

    def set_comboBox_currentData(self, combo_box, data_value):
        """根据数据值设置组合框选中项"""
        index = combo_box.findData(data_value)
        if index >= 0:
            combo_box.setCurrentIndex(index)

    def refresh_ports(self):
        """刷新串口列表"""

        # 获取当前所有端口
        current_ports = [port.portName() for port in QSerialPortInfo.availablePorts()]

        # 如果端口列表没有变化，直接返回
        if set(current_ports) == set(self.last_port_list):
            return

        # 保存当前端口列表用于下次比较
        self.last_port_list = current_ports.copy()

        # 获取下拉框当前的端口
        current_selection = self.ui.port_cb.currentText()

        # 清空下拉框
        self.ui.port_cb.clear()

        # 添加检测到的端口
        for port_name in current_ports:
            self.ui.port_cb.addItem(port_name)

        # 如果之前有选择，尝试恢复选择
        if current_selection and current_selection in current_ports:
            index = self.ui.port_cb.findText(current_selection)
            if index >= 0:
                self.ui.port_cb.setCurrentIndex(index)
                # 更新信息显示
                self.update_port_info(index)

        # 如果没有端口，显示提示
        if len(current_ports) == 0:
            self.ui.port_cb.addItem("未检测到串口")

    def get_port_info(self, port_name):
        """获取端口详细信息"""
        ports = QSerialPortInfo.availablePorts()
        for port in ports:
            if port.portName() == port_name:
                return {
                    'name': port.portName(),
                    'description': port.description() or '无描述',
                    'manufacturer': port.manufacturer() or '未知',
                    'serial': port.serialNumber() or '无',
                    'location': port.systemLocation(),
                    'vendor_id': f"0x{port.vendorIdentifier():04x}" if port.vendorIdentifier() else "未知",
                    'product_id': f"0x{port.productIdentifier():04x}" if port.productIdentifier() else "未知",
                    'is_busy': "是" if port.isBusy() else "否"
                }
        return {}

    def show_port_info(self, port_info):
        """在TextEdit中显示端口信息"""
        info_text = f"""设备描述: {port_info['description']}
制造商: {port_info['manufacturer']}
序列号: {port_info['serial']}
系统路径: {port_info['location']}
厂商ID: {port_info['vendor_id']}
产品ID: {port_info['product_id']}
占用状态: {port_info['is_busy']}"""

        self.ui.port_info_lEdit.setPlainText(info_text)

    def update_port_info(self, index):
        """更新端口信息显示"""
        if index >= 0:
            port_name = self.ui.port_cb.currentText()
            if port_name != "未检测到串口":
                port_info = self.get_port_info(port_name)
                self.show_port_info(port_info)
            else:
                self.ui.port_info_lEdit.setPlainText("未检测到可用串口设备")
        else:
            self.ui.port_info_lEdit.setPlainText("未选择串口设备")

    def closeEvent(self, event):
        """关闭时停止定时器"""
        self.port_infor_timer.stop()
        event.accept()
