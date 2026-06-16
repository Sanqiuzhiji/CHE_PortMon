# -*- coding: utf-8 -*-
from ui.windows.floating_connection_window import FloatingConnectionWindow


class UartWindow(FloatingConnectionWindow):
    def __init__(self, uart_widget, parent=None):
        super().__init__("UART Connection", uart_widget, parent)
