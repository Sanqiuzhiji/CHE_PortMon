# -*- coding: utf-8 -*-
from PyQt5.QtCore import QPoint, pyqtSignal
from PyQt5.QtWidgets import QTabBar, QTabWidget

from ui.windows.floating_connection_window import FloatingConnectionWindow


class DetachableTabBar(QTabBar):
    detach_requested = pyqtSignal(int, QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self._press_pos = QPoint()
        self._press_index = -1
        self._detach_started = False
        self._vertical_detach_threshold = 36

    def mousePressEvent(self, event):
        self._press_pos = event.pos()
        self._press_index = self.tabAt(event.pos())
        self._detach_started = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_index >= 0 and not self._detach_started:
            delta = event.pos() - self._press_pos
            horizontal = abs(delta.x())
            vertical = abs(delta.y())
            if vertical >= self._vertical_detach_threshold and vertical > horizontal:
                self._detach_started = True
                self.detach_requested.emit(self._press_index, event.globalPos())
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_pos = QPoint()
        self._press_index = -1
        self._detach_started = False
        super().mouseReleaseEvent(event)


class DetachableTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._detached_tabs = {}
        self._tab_bar = DetachableTabBar(self)
        self.setTabBar(self._tab_bar)
        self.setMovable(True)
        self.setDocumentMode(True)
        self._tab_bar.detach_requested.connect(self.detach_tab)

    def register_connection(self, key, title, page):
        index = self.addTab(page, title)
        self.tabBar().setTabData(index, key)
        return index

    def detach_tab(self, index, global_pos=None):
        if index < 0 or index >= self.count():
            return

        key = self.tabBar().tabData(index)
        title = self.tabText(index)
        page = self.widget(index)
        self.removeTab(index)
        page.setParent(None)
        page.show()

        window = FloatingConnectionWindow(f"{title} Connection", page, self)
        window.closed.connect(lambda key=key: self._reattach_tab(key))
        self._detached_tabs[key] = {
            "index": index,
            "page": page,
            "title": title,
            "window": window,
        }
        if global_pos is not None:
            window.move(global_pos)
        window.show()

    def _reattach_tab(self, key):
        tab = self._detached_tabs.pop(key, None)
        if tab is None:
            return

        window = tab["window"]
        page = tab["page"]
        title = tab["title"]
        index = min(tab["index"], self.count())
        restored_index = self.insertTab(index, page, title)
        self.tabBar().setTabData(restored_index, key)
        self.setCurrentIndex(restored_index)
        page.show()
        window.deleteLater()
