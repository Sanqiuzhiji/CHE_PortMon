import math
import time
import numpy as np
from PyQt5.QtWidgets import QMessageBox, QVBoxLayout
from PyQt5.QtCore import QTimer
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class MathFunctionSender:
    def __init__(self, serial_app):
        self.serial_app = serial_app
        self.ui = serial_app.ui

        # 数学函数类型映射
        self.math_functions = {
            "正弦波 (sin)": "sin",
            "余弦波 (cos)": "cos",
            "正切波 (tan)": "tan",
            "方波": "square",
            "三角波": "triangle",
            "锯齿波": "sawtooth",
            "指数函数 (exp)": "exp",
            "对数函数 (log)": "log"
        }

        # 发送相关属性
        self.data_points = []
        self.current_index = 0
        self.send_timer: QTimer = QTimer()
        self.send_timer.timeout.connect(self.send_next_point)
        self.send_interval = 100  # 默认发送间隔100ms

        # 图表相关属性
        self.figure = None
        self.canvas = None
        self.ax = None

        # 初始化数学函数界面
        self.init_math_function_ui()
        self.setup_chart()

    def init_math_function_ui(self):
        """初始化数学函数界面"""
        # 初始化函数类型下拉框
        self.ui.function_type_cb.clear()
        for display_name in self.math_functions.keys():
            self.ui.function_type_cb.addItem(display_name)

        # 设置默认参数值
        self.ui.start_value_lEdit.setText("0")
        self.ui.end_value_lEdit.setText("10")
        self.ui.step_lEdit.setText("0.1")
        self.ui.amplitude_lEdit.setText("1")
        self.ui.frequency_lEdit.setText("1")
        self.ui.period_lEdit.setText("1000")

        # 修改预览按钮文本
        self.ui.preview_btn.setText("图形预览")

    def setup_chart(self):
        """设置图表"""
        # 清除现有布局
        layout = self.ui.chart_container.layout()
        if layout:
            # 清除现有部件
            for i in reversed(range(layout.count())):
                layout.itemAt(i).widget().setParent(None)
        else:
            layout = QVBoxLayout(self.ui.chart_container)

        # 创建图表
        self.figure = Figure(figsize=(5, 4), dpi=80)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']  # 支持中文的字体
        plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号

        # 设置图表样式
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_title('函数图形预览')

        # 添加到布局
        layout.addWidget(self.canvas)

    def connect_math_signals(self):
        """连接数学函数信号（在SerialAppClass的connect_signals中调用）"""
        self.ui.preview_btn.clicked.connect(self.preview_math_function)
        self.ui.send_math_btn.clicked.connect(self.send_math_function)

    def preview_math_function(self):
        """图形预览数学函数"""
        try:
            # 获取参数
            function_type = self.math_functions[self.ui.function_type_cb.currentText()]
            start = float(self.ui.start_value_lEdit.text())
            end = float(self.ui.end_value_lEdit.text())
            step = float(self.ui.step_lEdit.text())
            amplitude = float(self.ui.amplitude_lEdit.text())
            frequency = float(self.ui.frequency_lEdit.text())

            # 验证参数
            if step <= 0:
                QMessageBox.warning(self.serial_app, "参数错误", "步长必须大于0")
                return
            if start >= end:
                QMessageBox.warning(self.serial_app, "参数错误", "起始值必须小于结束值")
                return

            # 生成更密集的数据点用于图形显示
            x_values = np.linspace(start, end, 1000)
            y_values = self.calculate_function_values(function_type, x_values, amplitude, frequency)

            # 绘制图形
            self.ax.clear()
            self.ax.plot(x_values, y_values, 'b-', linewidth=2)

            # 设置图表属性
            self.ax.grid(True, alpha=0.3)
            self.ax.set_xlabel('X')
            self.ax.set_ylabel('Y')

            # 设置支持中文的标题
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            self.ax.set_title(f'{self.ui.function_type_cb.currentText()} 图形')

            # 自动调整坐标轴范围
            self.ax.set_xlim(start, end)
            if len(y_values) > 0:
                y_min, y_max = np.min(y_values), np.max(y_values)
                y_range = y_max - y_min
                if y_range > 0:
                    self.ax.set_ylim(y_min - 0.1 * y_range, y_max + 0.1 * y_range)

            # 刷新图表
            self.canvas.draw()

            # 同时生成用于发送的数据点
            self.data_points = self.generate_math_function(
                function_type, start, end, step, amplitude, frequency
            )

        except ValueError as e:
            QMessageBox.warning(self.serial_app, "参数错误", "请输入有效的数值参数")
        except Exception as e:
            QMessageBox.critical(self.serial_app, "错误", f"生成函数图形时出错: {e}")

    def calculate_function_values(self, function_type, x_values, amplitude, frequency):
        """计算函数值（用于图形显示）"""
        if function_type == "sin":
            return amplitude * np.sin(2 * np.pi * frequency * x_values)
        elif function_type == "cos":
            return amplitude * np.cos(2 * np.pi * frequency * x_values)
        elif function_type == "tan":
            # 对tan函数进行特殊处理，避免奇点
            result = amplitude * np.tan(2 * np.pi * frequency * x_values)
            # 限制显示范围，避免过大的值
            result = np.clip(result, -10 * amplitude, 10 * amplitude)
            return result
        elif function_type == "square":
            return amplitude * np.sign(np.sin(2 * np.pi * frequency * x_values))
        elif function_type == "triangle":
            # 三角波
            phase = (x_values * frequency) % 1
            return amplitude * (2 * np.abs(2 * phase - 1) - 1)
        elif function_type == "sawtooth":
            # 锯齿波
            phase = (x_values * frequency) % 1
            return amplitude * (2 * phase - 1)
        elif function_type == "exp":
            return amplitude * np.exp(frequency * x_values)
        elif function_type == "log":
            # 对数函数，处理负值和零
            with np.errstate(divide='ignore', invalid='ignore'):
                result = amplitude * np.log(frequency * np.abs(x_values) + 1e-10)
                result = np.nan_to_num(result, nan=-10 * amplitude, posinf=10 * amplitude, neginf=-10 * amplitude)
            return result
        else:
            return np.zeros_like(x_values)

    def generate_math_function(self, function_type, start, end, step, amplitude, frequency):
        """生成数学函数数据点（用于发送）"""
        data_points = []
        x = start

        while x <= end:
            try:
                if function_type == "sin":
                    y = amplitude * math.sin(2 * math.pi * frequency * x)
                elif function_type == "cos":
                    y = amplitude * math.cos(2 * math.pi * frequency * x)
                elif function_type == "tan":
                    tan_x = 2 * math.pi * frequency * x
                    if abs(math.cos(tan_x)) > 1e-10:
                        y = amplitude * math.tan(tan_x)
                    else:
                        y = amplitude if math.sin(tan_x) > 0 else -amplitude
                elif function_type == "square":
                    y = amplitude if math.sin(2 * math.pi * frequency * x) >= 0 else -amplitude
                elif function_type == "triangle":
                    phase = x * frequency - math.floor(x * frequency)
                    if phase < 0.25:
                        y = 4 * amplitude * phase
                    elif phase < 0.75:
                        y = 2 * amplitude - 4 * amplitude * phase
                    else:
                        y = 4 * amplitude * phase - 4 * amplitude
                elif function_type == "sawtooth":
                    y = 2 * amplitude * (x * frequency - math.floor(x * frequency + 0.5))
                elif function_type == "exp":
                    y = amplitude * math.exp(frequency * x)
                elif function_type == "log":
                    if frequency * x > 0:
                        y = amplitude * math.log(frequency * x)
                    else:
                        y = -amplitude * 10
                else:
                    y = 0

                data_points.append((x, y))
                x += step

            except (ValueError, ZeroDivisionError):
                x += step
                continue

        return data_points

    def send_math_function(self):
        """开始逐个发送数学函数数据点"""
        if not self.serial_app.serial_process.is_open:
            QMessageBox.warning(self.serial_app, "提示", "请先打开串口")
            return

        try:
            # 获取参数
            function_type = self.math_functions[self.ui.function_type_cb.currentText()]
            start = float(self.ui.start_value_lEdit.text())
            end = float(self.ui.end_value_lEdit.text())
            step = float(self.ui.step_lEdit.text())
            amplitude = float(self.ui.amplitude_lEdit.text())
            frequency = float(self.ui.frequency_lEdit.text())

            # 验证参数
            if step <= 0:
                QMessageBox.warning(self.serial_app, "参数错误", "步长必须大于0")
                return
            if start >= end:
                QMessageBox.warning(self.serial_app, "参数错误", "起始值必须小于结束值")
                return

            # 生成数据
            self.data_points = self.generate_math_function(
                function_type, start, end, step, amplitude, frequency
            )

            if not self.data_points:
                QMessageBox.warning(self.serial_app, "错误", "未生成有效的数据点")
                return

            # 确保使用文本模式
            self.ui.hex_send_chb.setChecked(False)

            # 重置发送状态
            self.current_index = 0

            # 开始逐个发送
            self.start_sending_points()

        except ValueError as e:
            QMessageBox.warning(self.serial_app, "参数错误", "请输入有效的数值参数")
        except Exception as e:
            QMessageBox.critical(self.serial_app, "错误", f"发送数学函数数据时出错: {e}")

    def start_sending_points(self):
        """开始逐个发送数据点"""
        if not self.data_points:
            return

        # 更新按钮状态
        self.ui.send_math_btn.setText("停止发送")
        self.ui.send_math_btn.clicked.disconnect()
        self.ui.send_math_btn.clicked.connect(self.stop_sending)

        # 设置发送间隔
        try:
            interval_text = self.ui.period_lEdit.text().strip()
            if interval_text:
                self.send_interval = max(10, int(interval_text))
        except:
            self.send_interval = 100

        # 开始定时器
        self.send_timer.start(self.send_interval)

        # 显示开始消息
        self.serial_app.ui.statusbar.showMessage(
            f"开始发送 {len(self.data_points)} 个数据点，间隔 {self.send_interval}ms", 3000
        )

    def send_next_point(self):
        """发送下一个数据点"""
        if self.current_index >= len(self.data_points):
            self.stop_sending()
            self.serial_app.ui.statusbar.showMessage("数学函数数据发送完成", 3000)
            return

        # 获取当前数据点
        x, y = self.data_points[self.current_index]

        # 准备发送的数据
        data_to_send = f"{y:.6f}\n"

        # 更新发送文本框
        self.ui.send_tEdit.setPlainText(data_to_send.strip())
        self.serial_app.actual_text = data_to_send.strip()
        self.serial_app.format_to_display_mode()

        # 发送数据
        if self.serial_app.serial_process.send_data(data_to_send, "", False):
            progress = (self.current_index + 1) / len(self.data_points) * 100
            self.serial_app.ui.statusbar.showMessage(
                f"发送进度: {self.current_index + 1}/{len(self.data_points)} ({progress:.1f}%)", 1000
            )

        self.current_index += 1

    def stop_sending(self):
        """停止发送数据点"""
        self.send_timer.stop()
        self.ui.send_math_btn.setText("发送函数")
        self.ui.send_math_btn.clicked.disconnect()
        self.ui.send_math_btn.clicked.connect(self.send_math_function)
        self.serial_app.ui.statusbar.showMessage("数学函数发送已停止", 3000)
