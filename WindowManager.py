# -*- coding: utf-8 -*-
import sys

from PyQt5.QtWidgets import QApplication

from MainWindow import MainWindow


class WindowManagerClass:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")

        self.main_window = MainWindow(self)
        self.main_window.move(190, 135)
        self.main_window.show()

    def show_main_window(self):
        """Show the main application window."""
        self.main_window.show()

    def run(self):
        """Run the application."""
        sys.exit(self.app.exec_())

    def close(self):
        """Close the application."""
        self.app.quit()


if __name__ == "__main__":
    manager = WindowManagerClass()
    manager.run()
