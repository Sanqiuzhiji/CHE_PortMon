# -*- coding: utf-8 -*-
from datetime import datetime

# 正确的导入方式
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QTextEdit
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

		# 初始化端口列表
		self.refresh_ports()

		# 设置定时器，每2秒检查一次
		self.port_infor_timer: QTimer = QTimer()
		self.port_infor_timer.timeout.connect(self.refresh_ports)
		self.port_infor_timer.start(1000)

		self.connect_signals()

		# 延迟加载上次设置，确保端口列表已刷新
		QTimer.singleShot(10, self.load_last_settings)

		# 自动清空相关属性
		self.receive_data_size = 0
		self.max_size = 512 * 1024  # 512KB
		self.auto_clear_timer: QTimer = QTimer()
		self.auto_clear_timer.timeout.connect(self.comprehensive_auto_clear)
		self.auto_clear_interval = 100

		# 自动发送相关属性
		self.is_auto_sending = False
		self.auto_send_timer: QTimer = QTimer()
		self.auto_send_timer.timeout.connect(self.auto_send_function)

		# 发送区实际文本
		self.actual_text = ""

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
		# 添加背景图片（不影响输入）
		self.ui.send_tEdit.setStyleSheet("""
		    QTextEdit {
		        background-image: url(Serial_Port/source/send_tEdit_bg.png);
		        background-position: center;
		        background-repeat: no-repeat;
		        background-attachment: fixed;
		        background-origin: content;
		        background-clip: content;
		    }
		    QTextEdit:focus {
		        border: 2px solid #0078d4;
		    }
		""")
		# 添加背景图片（不影响输入）
		self.ui.send_hex_tEdit.setStyleSheet("""
		    QTextEdit {
		        background-image: url(Serial_Port/source/send_hex_tEdit_bg.png);
		        background-position: center;
		        background-repeat: no-repeat;
		        background-attachment: fixed;
		        background-origin: content;
		        background-clip: content;
		    }
		    QTextEdit:focus {
		        border: 2px solid #0078d4;
		    }
		""")
		# 添加焦点事件监听
		self.ui.send_tEdit.focusInEvent = self.send_text_edit_focus_in
		self.ui.send_tEdit.focusOutEvent = self.send_text_edit_focus_out

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
		self.ui.auto_clearReceive_chb.stateChanged.connect(self.on_auto_clear_changed)
		self.ui.auto_send_btn.clicked.connect(self.on_auto_send_changed)
		self.ui.auto_sendTime_lEdit.textChanged.connect(self.on_auto_send_time_changed)
		self.ui.port_cb.currentIndexChanged.connect(self.update_port_info_display)

		# 复选框信号 - 添加自动保存
		self.ui.hex_receive_chb.stateChanged.connect(self.on_hex_receive_changed)
		self.ui.hex_receive_chb.stateChanged.connect(self.auto_save_settings)
		self.ui.hex_send_chb.stateChanged.connect(self.on_hex_send_changed)
		self.ui.hex_send_chb.stateChanged.connect(self.auto_save_settings)
		self.ui.timestamp_chb.stateChanged.connect(self.on_timestamp_changed)
		self.ui.timestamp_chb.stateChanged.connect(self.auto_save_settings)
		self.ui.rts_chb.stateChanged.connect(self.on_flow_control_changed)
		self.ui.rts_chb.stateChanged.connect(self.auto_save_settings)
		self.ui.dtr_chb.stateChanged.connect(self.on_flow_control_changed)
		self.ui.dtr_chb.stateChanged.connect(self.auto_save_settings)
		self.ui.auto_clearReceive_chb.stateChanged.connect(self.auto_save_settings)

		# 端口和参数变化信号 - 添加自动保存
		self.ui.port_cb.currentTextChanged.connect(self.auto_save_settings)
		self.ui.baudrate_cb.currentTextChanged.connect(self.auto_save_settings)
		self.ui.parity_cb.currentTextChanged.connect(self.auto_save_settings)
		self.ui.databits_cb.currentTextChanged.connect(self.auto_save_settings)
		self.ui.stopbits_cb.currentTextChanged.connect(self.auto_save_settings)

	def auto_save_settings(self):
		"""自动保存设置"""
		self.save_current_settings()

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
		"""保存当前所有设置"""
		self.config_manager.save_all_settings(self)

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

		# 更新接收数据大小
		self.receive_data_size += len(data)

		if self.ui.hex_receive_chb.isChecked():
			# 十六进制显示
			hex_data = data.toHex().data().decode()
			formatted_hex = ' '.join([hex_data[i:i + 2] for i in range(0, len(hex_data), 2)])
			display_text = formatted_hex
		else:
			# 文本显示
			display_text = data.data().decode('utf-8', errors = 'ignore')

		# 添加时间戳
		if self.ui.timestamp_chb.isChecked():
			from datetime import datetime
			timestamp = datetime.now().strftime("[%H:%M:%S] ")
			display_text = timestamp + display_text

		# 追加到接收文本框
		self.append_to_receive(display_text)

	def append_to_receive(self, text):
		"""将文本追加到接收文本框"""
		cursor = self.ui.receive_tEdit.textCursor()
		cursor.movePosition(QTextCursor.End)
		cursor.insertText(text)
		self.ui.receive_tEdit.setTextCursor(cursor)
		self.ui.receive_tEdit.ensureCursorVisible()

	def send_data(self):
		"""发送数据"""
		if not self.serial_process.is_open:
			QMessageBox.warning(self, "提示", "请先打开串口")
			return

		if not self.actual_text:
			QMessageBox.information(self, "提示", "请输入要发送的数据")
			return

		is_hex = self.ui.hex_send_chb.isChecked()
		if self.serial_process.send_data(self.actual_text, is_hex):
			# 发送成功
			pass

	def send_file(self):
		"""发送文件"""
		file_path = self.ui.file_send_lEdit.text()
		if not file_path:
			QMessageBox.information(self, "提示", "请先选择要发送的文件")
			return

		if self.serial_process.send_file(file_path):
			self.ui.statusbar.showMessage("文件发送完成", 1000)  # 显示3秒

	def clear_receive_data(self):
		"""清空接收数据"""
		self.ui.receive_tEdit.clear()
		self.serial_process.reset_stats()

	def clear_send_data(self):
		"""清空发送数据"""
		current_text = self.ui.auto_send_btn.text()
		if current_text == "停止自动发送":
			self.on_auto_send_changed()
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
		# 先检查是否有预设的保存路径
		preset_path = self.ui.file_receive_lEdit.text().strip()

		if preset_path:
			# 使用预设路径直接保存
			try:
				with open(preset_path, 'w', encoding = 'utf-8') as f:
					f.write(self.ui.receive_tEdit.toPlainText())
				QMessageBox.information(self, "成功", f"数据已保存到: {preset_path}")
			except Exception as e:
				QMessageBox.critical(self, "错误", f"保存失败: {e}")
		else:
			# 没有预设路径，弹出文件选择对话框
			file_path, _ = QFileDialog.getSaveFileName(
				self, "保存接收数据", "", "文本文件 (*.txt);;所有文件 (*)"
			)

			if file_path:
				try:
					with open(file_path, 'w', encoding = 'utf-8') as f:
						f.write(self.ui.receive_tEdit.toPlainText())
					QMessageBox.information(self, "成功", "数据已保存")
				except Exception as e:
					QMessageBox.critical(self, "错误", f"保存失败: {e}")

	def select_receive_path(self):
		"""选择接收数据保存路径"""
		default_name = f"serial_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

		file_path, _ = QFileDialog.getSaveFileName(
			self, "设置接收数据保存路径", default_name, "文本文件 (*.txt)"
		)

		if file_path:
			self.ui.file_receive_lEdit.setText(file_path)
			self.auto_save_settings()

	def select_send_file(self):
		"""选择发送文件"""
		file_path, _ = QFileDialog.getOpenFileName(
			self, "选择要发送的文件", "", "所有文件 (*)"
		)

		if file_path:
			self.ui.file_send_lEdit.setText(file_path)
			self.auto_save_settings()  # 自动保存

	def on_hex_receive_changed(self, state):
		"""十六进制接收显示切换"""

		# 控制自动清空定时器
		if self.ui.auto_clearReceive_chb.isChecked():
			self.auto_clear_timer.start(self.auto_clear_interval)
		else:
			self.auto_clear_timer.stop()

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
		"""加载上次的所有设置"""
		last_settings = self.config_manager.load_user_settings()

		# 加载串口设置 - 智能选择端口
		serial_settings = last_settings.get("serial", {})
		saved_port = serial_settings.get("port", "")

		# 智能选择端口：如果保存的端口可用则使用，否则使用第一个可用端口
		if saved_port and self.config_manager.is_port_available(saved_port):
			self.ui.port_cb.setCurrentText(saved_port)
		else:
			# 获取第一个可用端口
			available_port = self.config_manager.get_available_port()
			if available_port:
				self.ui.port_cb.setCurrentText(available_port)

		# 加载其他串口参数
		self.ui.baudrate_cb.setCurrentText(serial_settings.get("baudrate", "115200"))
		self.ui.parity_cb.setCurrentText(serial_settings.get("parity", "无"))
		self.ui.databits_cb.setCurrentText(serial_settings.get("databits", "8"))
		self.ui.stopbits_cb.setCurrentText(serial_settings.get("stopbits", "1"))

		# 加载发送设置
		send_settings = last_settings.get("send", {})
		self.ui.hex_send_chb.setChecked(send_settings.get("hex_send", False))
		self.ui.auto_send_btn.setText("启动自动发送")

		# 加载接收设置
		receive_settings = last_settings.get("receive", {})
		self.ui.hex_receive_chb.setChecked(receive_settings.get("hex_receive", False))
		self.ui.timestamp_chb.setChecked(receive_settings.get("timestamp", False))
		self.ui.auto_clearReceive_chb.setChecked(receive_settings.get("auto_clear_receive", False))

		# 加载流控制
		flow_control = last_settings.get("flow_control", {})
		self.ui.rts_chb.setChecked(flow_control.get("rts", False))
		self.ui.dtr_chb.setChecked(flow_control.get("dtr", False))

		# 加载文件路径
		file_paths = last_settings.get("file_paths", {})
		self.ui.file_receive_lEdit.setText(file_paths.get("receive_save", ""))
		self.ui.file_send_lEdit.setText(file_paths.get("send_file", ""))

	def set_comboBox_currentData(self, combo_box, data_value):
		"""根据数据值设置组合框选中项"""
		index = combo_box.findData(data_value)
		if index >= 0:
			combo_box.setCurrentIndex(index)

	def update_port_info_display(self, index):
		"""更新端口信息显示"""
		port_name = self.ui.port_cb.currentText()

		# 检查是否是有效端口
		if port_name and port_name != "未检测到串口":
			port_info = self.get_port_info(port_name)
			if port_info:
				self.show_port_info(port_info)
			else:
				self.ui.port_info_lEdit.setPlainText("无法获取端口信息")
		else:
			self.ui.port_info_lEdit.setPlainText("未选择有效串口设备")

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

		# 如果没有端口，显示提示
		if len(current_ports) == 0:
			self.ui.port_cb.addItem("未检测到串口")
			self.ui.port_info_lEdit.setPlainText("未检测到可用串口设备")
			return

		# 智能选择端口
		if current_selection and current_selection in current_ports:
			# 如果之前选择的端口仍然存在，保持选择
			index = self.ui.port_cb.findText(current_selection)
			if index >= 0:
				self.ui.port_cb.setCurrentIndex(index)
		else:
			# 否则尝试使用保存的端口
			last_settings = self.config_manager.load_user_settings()
			saved_port = last_settings.get("serial", {}).get("port", "")
			if saved_port and saved_port in current_ports:
				index = self.ui.port_cb.findText(saved_port)
				if index >= 0:
					self.ui.port_cb.setCurrentIndex(index)
			else:
				# 否则选择第一个端口
				self.ui.port_cb.setCurrentIndex(0)

		# 更新信息显示 - 使用新的方法
		self.update_port_info_display(self.ui.port_cb.currentIndex())

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
占用状态: {port_info['is_busy']}
制造商: {port_info['manufacturer']}
序列号: {port_info['serial']}
系统路径: {port_info['location']}
厂商ID: {port_info['vendor_id']}
产品ID: {port_info['product_id']}"""

		self.ui.port_info_lEdit.setPlainText(info_text)

	def on_auto_clear_changed(self, state):
		"""自动清空复选框状态改变"""
		if state:
			self.auto_clear_timer.start(self.auto_clear_interval)
		else:
			self.auto_clear_timer.stop()

	def on_auto_send_changed(self):
		"""自动发送按钮状态改变"""
		current_text = self.ui.auto_send_btn.text()

		if current_text == "启动自动发送":
			"""启动自动发送"""
			if not self.serial_process.is_open:
				QMessageBox.warning(self, "错误", "请先打开串口")
				return

			send_text = self.ui.send_tEdit.toPlainText()
			if not send_text:
				QMessageBox.warning(self, "提示", "请输入要发送的数据")
				return

			try:
				interval_text = self.ui.auto_sendTime_lEdit.text().strip()
				if not interval_text:
					QMessageBox.warning(self, "提示", "请输入发送间隔时间")
					return

				interval_ms = int(interval_text)

				if interval_ms < 10:
					QMessageBox.warning(self, "提示", "发送间隔太短，请设置至少10毫秒")
					return

				# 启动定时器
				self.auto_send_timer.start(interval_ms)
				self.is_auto_sending = True
				self.ui.auto_send_btn.setText("停止自动发送")

			except ValueError:
				QMessageBox.warning(self, "错误", "请输入有效的数字")

		elif current_text == "停止自动发送":
			"""停止自动发送"""
			self.auto_send_timer.stop()
			self.is_auto_sending = False
			self.ui.auto_send_btn.setText("启动自动发送")

	def comprehensive_auto_clear(self):
		"""综合自动清空策略"""
		if self.receive_data_size > self.max_size:
			self.ui.receive_tEdit.clear()
			self.receive_data_size = 0

	def auto_send_function(self):
		"""自动发送数据"""
		self.send_data()

	def on_auto_send_time_changed(self, text):
		"""自动发送间隔时间改变"""
		if text.strip():  # 非空输入
			try:
				interval_ms = int(text)
				if interval_ms < 10:
					QMessageBox.warning(self, "提示", "发送间隔太短，请设置至少10毫秒")
					self.ui.auto_sendTime_lEdit.setText("10")
				else:
					self.auto_send_timer.start(interval_ms)
			except ValueError:
				pass  # 输入的不是数字

	def send_text_edit_focus_in(self, event):
		"""发送文本框获得焦点 - 显示实际换行"""
		# 先调用父类方法
		QTextEdit.focusInEvent(self.ui.send_tEdit, event)
		# print("send_text_edit_focus_in")
		# 从格式化显示恢复为实际文本
		self.restore_actual_text()

	def send_text_edit_focus_out(self, event):
		"""发送文本框失去焦点 - 显示[\n]标记"""
		# 先调用父类方法
		QTextEdit.focusOutEvent(self.ui.send_tEdit, event)
		# print("send_text_edit_focus_out")
		# 格式化为显示模式
		self.format_to_display_mode()

	def restore_actual_text(self):
		"""恢复实际文本显示（编辑模式）"""
		# 还原实际文本
		# print("actual_text:",self.actual_text)
		self.ui.send_tEdit.setPlainText(self.actual_text)

	def format_to_display_mode(self):
		"""格式化为显示模式（非编辑模式）"""
		self.actual_text = self.ui.send_tEdit.toPlainText()
		# print("actual_text",  self.actual_text)
		# 按真正的换行符分割文本
		lines =  self.actual_text.split('\n')
		display_lines = []
		# print("lines", lines)
		line_number = 0

		if all(line == '' for line in lines):
			for i in range(0, len(lines) - 1):
				display_lines.append('[\\n]\n')
		else:
			# 处理开头的空行
			for line_number, line in enumerate(lines):
				if line == '':
					display_lines.append('[\\n]\n')
				else:
					break
			# 从 line_number 开始继续处理剩余行
			for i in range(line_number, len(lines)):
				line = lines[i]
				if line != '':
					if i < len(lines) - 1:
						display_lines.append(line + '\n')
					else:
						display_lines.append(line)
				else:
					display_lines.append('[\\n]\n')

		display_text = ''.join(display_lines)
		# print("display_text", display_text)
		self.ui.send_tEdit.blockSignals(True)
		self.ui.send_tEdit.setPlainText(display_text)
		self.ui.send_tEdit.blockSignals(False)

	def closeEvent(self, event):
		"""关闭时停止定时器"""
		self.port_infor_timer.stop()
		event.accept()
