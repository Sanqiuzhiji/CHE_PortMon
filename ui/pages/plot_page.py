# -*- coding: utf-8 -*-
import re

from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from services.plot_layout_service import PlotLayoutService
from ui.widgets.detachable_page_tab_widget import DetachablePageTabWidget
from ui.widgets.plot_widgets import PlotCanvas

class PlotWorkspacePage(QWidget):
    def __init__(self, channel_manager=None, name="Page 1", parent=None):
        super().__init__(parent)
        self.page_name = name
        self.channel_manager = channel_manager
        self.setObjectName("plotWorkspacePage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.canvas = PlotCanvas(channel_manager=channel_manager, parent=self)
        layout.addWidget(self.canvas)

    def set_page_name(self, name):
        self.page_name = name

    def to_dict(self):
        return {
            "name": self.page_name,
            "grid_size": self.canvas.grid_size(),
            "snap_to_grid": self.canvas.snap_to_grid(),
            "controls": [control.to_dict() for control in self.canvas.controls()],
        }

    def clear_canvas(self):
        self.canvas.clear_controls()


class PlotPage(QWidget):
    command_generated = pyqtSignal(object)

    def __init__(self, channel_manager=None, layout_service=None):
        super().__init__()
        self.channel_manager = channel_manager
        self.layout_service = layout_service or PlotLayoutService()
        self._page_count = 0
        self._build_ui()
        self._connect_signals()
        self._sync_empty_state()

    def _build_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(18, 14, 18, 14)
        self.root_layout.setSpacing(10)

        self.title_label = QLabel("Plot", self)
        self.title_label.setObjectName("plotTitleLabel")
        self.root_layout.addWidget(self.title_label)

        self.toolbar_frame = QFrame(self)
        self.toolbar_frame.setObjectName("plotToolbarFrame")
        toolbar_layout = QHBoxLayout(self.toolbar_frame)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(8)
        self.new_page_button = QToolButton(self.toolbar_frame)
        self.new_page_button.setText("新建页")
        self.delete_page_button = QToolButton(self.toolbar_frame)
        self.delete_page_button.setText("删除页")
        self.clear_page_button = QToolButton(self.toolbar_frame)
        self.clear_page_button.setText("清除页")
        self.save_layout_button = QToolButton(self.toolbar_frame)
        self.save_layout_button.setText("保存页")
        self.load_layout_button = QToolButton(self.toolbar_frame)
        self.load_layout_button.setText("导入页")
        for button in (
            self.new_page_button,
            self.delete_page_button,
            self.clear_page_button,
            self.save_layout_button,
            self.load_layout_button,
        ):
            toolbar_layout.addWidget(button)
        toolbar_layout.addSpacing(12)
        toolbar_layout.addWidget(QLabel("Grid", self.toolbar_frame))
        self.grid_size_spinbox = QSpinBox(self.toolbar_frame)
        self.grid_size_spinbox.setObjectName("plotGridSizeSpinBox")
        self.grid_size_spinbox.setRange(5, 100)
        self.grid_size_spinbox.setSingleStep(5)
        self.grid_size_spinbox.setSuffix(" px")
        self.grid_size_spinbox.setValue(20)
        self.grid_size_spinbox.setFixedWidth(86)
        toolbar_layout.addWidget(self.grid_size_spinbox)
        self.snap_to_grid_check = QCheckBox("Snap", self.toolbar_frame)
        self.snap_to_grid_check.setObjectName("plotSnapToGridCheck")
        self.snap_to_grid_check.setChecked(True)
        toolbar_layout.addWidget(self.snap_to_grid_check)
        toolbar_layout.addStretch(1)
        self.root_layout.addWidget(self.toolbar_frame)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(10)
        self.left_panel = QVBoxLayout()
        self.left_panel.setContentsMargins(0, 0, 0, 0)
        self.left_panel.setSpacing(8)
        self.page_tabs = DetachablePageTabWidget(self)
        self.page_tabs.setObjectName("plotPageTabs")
        self.left_panel.addWidget(self.page_tabs)
        body.addLayout(self.left_panel, 1)

        self.channel_panel = PlotChannelPanel(self.channel_manager, self)
        self.channel_panel.setObjectName("plotChannelPanel")
        body.addWidget(self.channel_panel, 0)
        self.root_layout.addLayout(body, 1)

    def _connect_signals(self):
        self.new_page_button.clicked.connect(self.add_page)
        self.delete_page_button.clicked.connect(self.delete_current_page)
        self.clear_page_button.clicked.connect(self.clear_current_page)
        self.save_layout_button.clicked.connect(self.save_layout)
        self.load_layout_button.clicked.connect(self.load_layout)
        self.page_tabs.currentChanged.connect(self._handle_current_changed)
        self.grid_size_spinbox.valueChanged.connect(self._handle_grid_size_changed)
        self.snap_to_grid_check.toggled.connect(self._handle_snap_to_grid_changed)

    def _load_or_create_layout(self):
        self._sync_empty_state()

    def _handle_current_changed(self, *_args):
        current = self.current_page_widget()
        if current is not None:
            self.channel_panel.set_current_control(None)
            self._sync_grid_controls_from_canvas(current.canvas)

    def add_page(self, name=None):
        page_name = name or self._next_page_name()
        page = PlotWorkspacePage(channel_manager=self.channel_manager, name=page_name, parent=self)
        page.canvas.command_generated.connect(self.command_generated.emit)
        page.canvas.set_grid_size(self.grid_size_spinbox.value())
        page.canvas.set_snap_to_grid(self.snap_to_grid_check.isChecked())
        self.page_tabs.add_page(page_name, page_name, page)
        self._sync_empty_state()
        return page

    def _current_canvas(self):
        current = self.current_page_widget()
        if current is None:
            return None
        return current.canvas

    def _handle_grid_size_changed(self, value):
        canvas = self._current_canvas()
        if canvas is not None:
            canvas.set_grid_size(value)

    def _handle_snap_to_grid_changed(self, checked):
        canvas = self._current_canvas()
        if canvas is not None:
            canvas.set_snap_to_grid(checked)

    def _sync_grid_controls_from_canvas(self, canvas):
        self.grid_size_spinbox.blockSignals(True)
        self.snap_to_grid_check.blockSignals(True)
        self.grid_size_spinbox.setValue(canvas.grid_size())
        self.snap_to_grid_check.setChecked(canvas.snap_to_grid())
        self.grid_size_spinbox.blockSignals(False)
        self.snap_to_grid_check.blockSignals(False)

    def _next_page_name(self):
        max_index = 0
        for title, _page in self.page_tabs.all_pages():
            match = re.fullmatch(r"Page\s+(\d+)", title.strip())
            if match:
                max_index = max(max_index, int(match.group(1)))
        return f"Page {max_index + 1}"

    def current_page_widget(self):
        return self.page_tabs.currentWidget()

    def delete_current_page(self):
        if self.page_tabs.count() == 0:
            return
        self.page_tabs.remove_tab(self.page_tabs.currentIndex())
        self._sync_empty_state()

    def clear_current_page(self):
        current = self.current_page_widget()
        if current is not None and hasattr(current, "clear_canvas"):
            current.clear_canvas()

    def save_layout(self):
        current = self.current_page_widget()
        if current is None:
            return

        page_data = current.to_dict()
        page_data["name"] = self.page_tabs.tabText(self.page_tabs.currentIndex())

        try:
            path = self.layout_service.save_page(page_data)
        except OSError as exc:
            QMessageBox.warning(self, "Save Plot Page", f"Save failed: {exc}")
            return

        QMessageBox.information(
            self,
            "Save Plot Page",
            f"已保存到：{path}",
        )

    def _current_layout_data(self):
        layout = {"pages": []}
        for title, page in self.page_tabs.all_pages():
            if page is None:
                continue
            page_dict = page.to_dict()
            page_dict["name"] = title
            layout["pages"].append(page_dict)
        return layout

    def load_layout(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Plot Layout",
            str(self.layout_service.pages_dir),
            "Plot Layout (*.json);;All Files (*)",
        )
        if not path:
            return
        try:
            layout = self.layout_service.load_layout_from(path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Import Plot Layout", f"Import failed: {exc}")
            return
        if isinstance(layout, dict) and "pages" not in layout and isinstance(layout.get("controls"), list):
            layout = {"pages": [layout]}
        if not isinstance(layout, dict) or not isinstance(layout.get("pages"), list):
            QMessageBox.warning(self, "Import Plot Layout", "Invalid plot layout file.")
            return
        self._append_layout_data(layout)

    def _load_layout_data(self, layout):
        self.page_tabs.close_all_floating()
        while self.page_tabs.count():
            self.page_tabs.remove_tab(0)
        self._append_layout_data(layout)

    def _append_layout_data(self, layout):
        pages = layout.get("pages") or []
        for page_data in pages:
            page_name = str(page_data.get("name", "Page")).strip() or "Page"
            self.page_tabs.remove_page_by_title(page_name)
            page = self.add_page(page_name)
            page.canvas.set_grid_size(int(page_data.get("grid_size", 20)))
            page.canvas.set_snap_to_grid(bool(page_data.get("snap_to_grid", True)))
            for control_data in page_data.get("controls", []):
                control = page.canvas.add_control(
                    control_data.get("type", "toggle"),
                    pos=QPoint(
                        int(control_data.get("x", 40)),
                        int(control_data.get("y", 40)),
                    ),
                    config=control_data.get("config", {}),
                    control_id=control_data.get("id"),
                    restore_geometry=True,
                )

                control.resize(
                    int(control_data.get("w", control.width())),
                    int(control_data.get("h", control.height())),
                )
                control.show()
        current = self.current_page_widget()
        if current is not None:
            self._sync_grid_controls_from_canvas(current.canvas)
        self._sync_empty_state()

    def _sync_empty_state(self):
        has_pages = self.page_tabs.count() > 0
        self.delete_page_button.setEnabled(has_pages)
        self.clear_page_button.setEnabled(has_pages)
        self.save_layout_button.setEnabled(has_pages)
        self.grid_size_spinbox.setEnabled(has_pages)
        self.snap_to_grid_check.setEnabled(has_pages)


class PlotChannelRow(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, channel, parent=None):
        super().__init__(parent)
        self.channel = channel
        self.setObjectName("plotChannelRow")
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        self.color_block = QFrame(self)
        self.color_block.setFixedSize(10, 10)
        self.color_block.setStyleSheet(f"background: {channel.color}; border-radius: 3px;")
        self.name_label = QLabel(channel.key, self)
        self.value_label = QLabel("0.0000", self)
        layout.addWidget(self.color_block)
        layout.addWidget(self.name_label)
        layout.addStretch(1)
        layout.addWidget(self.value_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.channel.key)
        super().mousePressEvent(event)

    def update_channel(self, channel):
        self.channel = channel
        self.color_block.setStyleSheet(f"background: {channel.color}; border-radius: 3px;")
        self.name_label.setText(channel.name)
        self.value_label.setText(f"{channel.display_value:.4f}")
        self.setEnabled(channel.enabled)


class PlotChannelPanel(QFrame):
    def __init__(self, channel_manager=None, parent=None):
        super().__init__(parent)
        self.channel_manager = channel_manager
        self._rows = {}
        self._current_key = None
        self.setMinimumWidth(260)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        title = QLabel("Channels", self)
        title.setObjectName("protocolPanelTitleLabel")
        layout.addWidget(title)
        self.rows_container = QVBoxLayout()
        self.rows_container.setSpacing(6)
        layout.addLayout(self.rows_container)
        layout.addStretch(1)
        self.config_frame = QFrame(self)
        config_layout = QVBoxLayout(self.config_frame)
        config_layout.setContentsMargins(0, 0, 0, 0)
        self.name_edit = QLineEdit(self.config_frame)
        self.color_edit = QLineEdit(self.config_frame)
        self.gain_edit = QLineEdit(self.config_frame)
        self.offset_edit = QLineEdit(self.config_frame)
        self.apply_button = QPushButton("Apply", self.config_frame)
        form = QFormLayout()
        form.addRow("Name", self.name_edit)
        form.addRow("Color", self.color_edit)
        form.addRow("Gain", self.gain_edit)
        form.addRow("Offset", self.offset_edit)
        config_layout.addLayout(form)
        config_layout.addWidget(self.apply_button)
        layout.addWidget(self.config_frame)
        self.apply_button.clicked.connect(self._apply_config)
        if self.channel_manager is not None:
            self.channel_manager.channels_changed.connect(self._rebuild)
            self._rebuild(self.channel_manager.channels())

    def set_current_control(self, control):
        self._current_key = None

    def _rebuild(self, channels):
        while self.rows_container.count():
            item = self.rows_container.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._rows.clear()
        for channel in channels:
            row = PlotChannelRow(channel, self)
            row.clicked.connect(self._select_channel)
            row.update_channel(channel)
            self.rows_container.addWidget(row)
            self._rows[channel.key] = row
        if channels:
            if self._current_key not in self._rows:
                self._current_key = channels[0].key
            self._update_editor()

    def _select_channel(self, key):
        self._current_key = key
        self._update_editor()

    def _update_editor(self):
        if self.channel_manager is None or self._current_key is None:
            return
        channel = self.channel_manager.channel_by_key(self._current_key)
        if channel is None:
            return
        self.name_edit.setText(channel.name)
        self.color_edit.setText(channel.color)
        self.gain_edit.setText(f"{channel.gain:.4f}")
        self.offset_edit.setText(f"{channel.offset:.4f}")

    def _apply_config(self):
        if self.channel_manager is None or self._current_key is None:
            return
        self.channel_manager.update_channel_config(
            self._current_key,
            name=self.name_edit.text().strip() or self._current_key,
            color=self.color_edit.text().strip() or None,
            gain=float(self.gain_edit.text() or "1.0"),
            offset=float(self.offset_edit.text() or "0.0"),
        )
