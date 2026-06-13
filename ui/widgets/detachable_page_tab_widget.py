# -*- coding: utf-8 -*-
from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QInputDialog,
    QMenu,
    QTabBar,
    QTabWidget,
)

from ui.windows.floating_page_window import FloatingPageWindow


class DetachablePageTabBar(QTabBar):
    detach_requested = pyqtSignal(int, QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self._press_pos = QPoint()
        self._press_index = -1
        self._detach_threshold = 36
        self._detach_started = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.pos()
            self._press_index = self.tabAt(event.pos())
            self._detach_started = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_index >= 0 and not self._detach_started:
            delta = event.pos() - self._press_pos
            horizontal = abs(delta.x())
            vertical = abs(delta.y())
            if vertical >= self._detach_threshold and vertical > horizontal:
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

    def contextMenuEvent(self, event):
        index = self.tabAt(event.pos())
        if index < 0:
            return
        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        float_action = menu.addAction("Float")
        close_action = menu.addAction("Close")
        action = menu.exec_(event.globalPos())
        if action == rename_action:
            title, ok = QInputDialog.getText(self, "Rename Page", "Page name:", text=self.tabText(index))
            if ok and title.strip():
                self.parentWidget().rename_tab(index, title.strip())
        elif action == float_action:
            self.parentWidget().detach_tab(index)
        elif action == close_action:
            self.parentWidget().remove_tab(index)


class DetachablePageTabWidget(QTabWidget):
    page_detached = pyqtSignal(str)
    page_reattached = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self._floating_windows = {}
        self._page_keys = {}
        self._page_titles = {}
        self._tab_bar = DetachablePageTabBar(self)
        self._tab_bar.detach_requested.connect(self.detach_tab)
        self.setTabBar(self._tab_bar)
        self.setMovable(True)
        self.setDocumentMode(True)
        self.tabCloseRequested.connect(self.remove_tab)

    def add_page(self, key, title, widget):
        index = self.addTab(widget, title)
        self._page_keys[widget] = key
        self._page_titles[widget] = title
        return index

    def page_widget(self, index):
        return self.widget(index)

    def page_widgets(self):
        return [self.widget(index) for index in range(self.count())]

    def all_pages(self):
        pages = []
        for index in range(self.count()):
            widget = self.widget(index)
            if widget is not None:
                pages.append((self.tabText(index), widget))
        for key, window in self._floating_windows.items():
            widget = window.centralWidget()
            if widget is not None:
                pages.append((window.windowTitle(), widget))
        return pages

    def rename_tab(self, index, title):
        widget = self.widget(index)
        if widget is None:
            return
        self.setTabText(index, title)
        self._page_titles[widget] = title
        if hasattr(widget, "set_page_name"):
            widget.set_page_name(title)

    def remove_tab(self, index):
        widget = self.widget(index)
        if widget is None:
            return
        self.removeTab(index)
        widget.deleteLater()

    def detach_tab(self, index, global_pos=None):
        widget = self.widget(index)
        if widget is None:
            return
        title = self.tabText(index)
        key = self._page_keys.get(widget, title)
        self.removeTab(index)
        window = FloatingPageWindow(title, widget)
        if global_pos is not None:
            window.move(global_pos)
        window.closed.connect(lambda w=widget, t=title, k=key, i=index: self._reattach_tab(w, t, k, i))
        self._floating_windows[key] = window
        self.page_detached.emit(title)
        window.show()

    def _reattach_tab(self, widget, title, key, index):
        if widget is None:
            return
        if index < 0 or index > self.count():
            index = self.count()
        self.insertTab(index, widget, title)
        self._page_keys[widget] = key
        self._page_titles[widget] = title
        self._floating_windows.pop(key, None)
        self.page_reattached.emit(title)

    def close_all_floating(self):
        for window in list(self._floating_windows.values()):
            window.close()
