# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QMainWindow
from PyQt5.uic.properties import QtWidgets

from Serial_Port.Serial_MainWindow import Ui_Serial_MainWindow
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from WindowManager import WindowManager_class


class SerialApp_class(QMainWindow):
	def __init__(self, window_manager: 'WindowManager_class'):
		super().__init__()
		self.window_manager: WindowManager_class = window_manager

		# 设置UI界面
		self.ui = Ui_Serial_MainWindow()
		self.ui.setupUi(self)
