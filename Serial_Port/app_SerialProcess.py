# serial_process.py
# -*- coding: utf-8 -*-
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QIODevice, QByteArray
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
import os


class SerialProcess(QObject):
    """串口处理类"""

    # 定义信号
    data_received = pyqtSignal(QByteArray)
    port_opened = pyqtSignal()  # 串口打开信号
    port_closed = pyqtSignal()  # 串口关闭信号
    error_occurred = pyqtSignal(str)  # 错误发生信号

    def __init__(self):
        super().__init__()
        self.serial = QSerialPort()
        self.is_open = False
        self.is_paused = False
        self.receive_count = 0
        self.send_count = 0

        # 自动发送定时器
        self.auto_send_timer: QTimer = QTimer()
        self.auto_send_timer.timeout.connect(self.auto_send_data)
        self.auto_send_interval = 1000  # 默认1秒

        # 连接串口信号
        self.serial.readyRead.connect(self.read_data)
        self.serial.errorOccurred.connect(self.handle_error)

    def open_port(self, port_name, baud_rate, data_bits, parity, stop_bits, flow_control):
        """打开串口"""
        try:
            if self.serial.isOpen():
                self.serial.close()

            # 设置串口参数
            self.serial.setPortName(port_name)
            self.serial.setBaudRate(baud_rate)
            self.serial.setDataBits(data_bits)
            self.serial.setParity(parity)
            self.serial.setStopBits(stop_bits)
            self.serial.setFlowControl(flow_control)

            # 打开串口
            if self.serial.open(QIODevice.ReadWrite):
                self.is_open = True
                self.port_opened.emit()
                return True
            else:
                error_msg = f"无法打开串口 {port_name}"
                print(error_msg)  # 调试信息
                self.error_occurred.emit(error_msg)
                return False


        except Exception as e:
            error_msg = f"打开串口错误: {str(e)}"
            print(error_msg)  # 调试信息
            self.error_occurred.emit(error_msg)
            return False

    def close_port(self):
        """关闭串口"""
        if self.serial.isOpen():
            self.serial.close()
            self.is_open = False
            self.port_closed.emit()

    def read_data(self):
        """读取串口数据"""
        if self.is_paused or not self.serial.isOpen():
            return

        try:
            # 读取所有可用数据
            data = self.serial.readAll()
            if data:
                self.receive_count += data.size()
                self.data_received.emit(data)
        except Exception as e:
            self.error_occurred.emit(f"读取数据错误: {str(e)}")

    def send_data(self, data, data_hex, is_hex=False):
        """发送数据"""
        if not self.serial.isOpen():
            self.error_occurred.emit("串口未打开")
            return False

        try:
            if is_hex:
                # 十六进制发送
                data_hex = data_hex.replace(' ', '').replace('\n', '').replace('\r', '')
                # print(f"十六进制数据: {data_hex}, 长度: {len(data_hex)}")

                if len(data_hex) % 2 != 0:
                    # 自动在前面补0，使其长度为偶数
                    data_hex = '0' + data_hex

                byte_data = bytes.fromhex(data_hex)
            else:
                # 文本发送
                byte_data = data.encode('utf-8')

            # 发送数据
            bytes_written = self.serial.write(byte_data)
            if bytes_written > 0:
                self.send_count += bytes_written
                self.serial.flush()  # 确保数据发送完成
                return True
            else:
                self.error_occurred.emit("发送数据失败")
                return False

        except Exception as e:
            self.error_occurred.emit(f"发送数据错误: {str(e)}")
            return False

    def send_file(self, file_path):
        """发送文件"""
        if not os.path.exists(file_path):
            self.error_occurred.emit(f"文件不存在: {file_path}")
            return False

        try:
            with open(file_path, 'rb') as file:
                content = file.read()
                return self.send_data(content.hex(), is_hex=True)
        except Exception as e:
            self.error_occurred.emit(f"发送文件错误: {str(e)}")
            return False

    def set_flow_control(self, rts_state, dtr_state):
        """设置流控制"""
        if self.serial.isOpen():
            self.serial.setRequestToSend(rts_state)
            self.serial.setDataTerminalReady(dtr_state)

    def set_auto_send(self, enabled, interval=1000):
        """设置自动发送"""
        self.auto_send_interval = interval

        if enabled:
            self.auto_send_timer.start(interval)
        else:
            self.auto_send_timer.stop()

    def auto_send_data(self):
        """自动发送数据（需要外部设置发送内容）"""
        # 这个功能需要主界面提供发送内容
        pass

    def pause_receive(self, paused):
        """暂停/恢复接收"""
        self.is_paused = paused

    def handle_error(self, error):
        """处理串口错误"""
        # 忽略 NoError 情况
        if error == QSerialPort.SerialPortError.NoError:
            return

        error_str = ""
        if error == QSerialPort.SerialPortError.ResourceError:
            error_str = "资源错误，串口可能被拔出"
        elif error == QSerialPort.SerialPortError.PermissionError:
            error_str = "权限错误，无法访问串口"
        elif error == QSerialPort.SerialPortError.OpenError:
            error_str = "打开串口错误"
        elif error == QSerialPort.SerialPortError.WriteError:
            error_str = "写入串口错误"
        elif error == QSerialPort.SerialPortError.ReadError:
            error_str = "读取串口错误"
        elif error == QSerialPort.SerialPortError.UnknownError:
            error_str = "未知串口错误"
        else:
            error_str = f"串口错误: {self.serial.errorString()}"

        # 只有当有实际错误时才发射信号
        if error_str:
            self.error_occurred.emit(error_str)

        # 如果串口打开时发生严重错误，关闭串口
        if self.serial.isOpen() and error in [
            QSerialPort.SerialPortError.ResourceError,
            QSerialPort.SerialPortError.PermissionError,
            QSerialPort.SerialPortError.OpenError
        ]:
            self.close_port()

    def get_port_info(self, port_name):
        """获取串口信息"""
        ports = QSerialPortInfo.availablePorts()
        for port in ports:
            if port.portName() == port_name:
                return {
                    'description': port.description() or '无描述',
                    'manufacturer': port.manufacturer() or '未知',
                    'serial_number': port.serialNumber() or '无',
                    'location': port.systemLocation(),
                    'vendor_id': f"0x{port.vendorIdentifier():04x}" if port.vendorIdentifier() else "未知",
                    'product_id': f"0x{port.productIdentifier():04x}" if port.productIdentifier() else "未知",
                    'is_busy': "是" if port.isBusy() else "否"
                }
        return {}

    def get_stats(self):
        """获取统计信息"""
        return {
            'receive_count': self.receive_count,
            'send_count': self.send_count
        }

    def reset_stats(self):
        """重置统计信息"""
        self.receive_count = 0
        self.send_count = 0
