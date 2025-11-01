# -*- coding: utf-8 -*-
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMainWindow
from PyQt5.uic.properties import QtWidgets
from PyQt5.QtSerialPort import QSerialPortInfo

from Serial_Port.Serial_MainWindow import Ui_Serial_MainWindow
from Serial_Port.config_manager import JSONConfigManager
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

        # 连接端口选择变化信号
        self.ui.port_cb.currentIndexChanged.connect(self.update_port_info)

        self.ui.open_btn.clicked.connect(self.on_open_clicked)

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

        self.ui.port_info_ledit.setPlainText(info_text)

    def update_port_info(self, index):
        """更新端口信息显示"""
        if index >= 0:
            port_name = self.ui.port_cb.currentText()
            if port_name != "未检测到串口":
                port_info = self.get_port_info(port_name)
                self.show_port_info(port_info)
            else:
                self.ui.port_info_ledit.setPlainText("未检测到可用串口设备")
        else:
            self.ui.port_info_ledit.setPlainText("未选择串口设备")

    def closeEvent(self, event):
        """关闭时停止定时器"""
        self.port_infor_timer.stop()
        event.accept()
