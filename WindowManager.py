# -*- coding: utf-8 -*-
import sys
import os
from PyQt5.QtWidgets import QApplication, QStackedWidget

# 加入窗口类
from Serial_Port.app_SerialWindows import SerialAppClass


class WindowManagerClass:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")

        # 使用堆栈管理窗口
        self.stacked_widget = QStackedWidget()

        # 创建窗口
        self.serial_port_window = SerialAppClass(self)

        # 添加到堆栈
        self.stacked_widget.addWidget(self.serial_port_window)

        # 设置初始窗口
        self.stacked_widget.setCurrentWidget(self.serial_port_window)
        # 使用窗口的实际尺寸设置堆栈大小
        width, height = self.serial_port_window.design_size
        self.stacked_widget.resize(width, height)
        self.stacked_widget.move(240 * 4 - 50, 135)
        self.stacked_widget.show()

    def show_main_window(self):
        """显示主窗口"""
        self.stacked_widget.setCurrentWidget(self.serial_port_window)

    def run(self):
        """运行应用程序"""
        sys.exit(self.app.exec_())

    def close(self):
        """关闭应用程序"""
        self.app.quit()


# 主入口
if __name__ == "__main__":
    manager = WindowManagerClass()
    manager.run()
