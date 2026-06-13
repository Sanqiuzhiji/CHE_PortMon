# -*- coding: utf-8 -*-
from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


DRAG_THRESHOLD = 8


FIELD_TEMPLATES = [
    {"label": "header", "kind": "Header", "data_type": "hex", "length": 2, "color": "#4cc9f0"},
    {"label": "frameId", "kind": "FrameId", "data_type": "uint8", "length": 1, "color": "#4895ef"},
    {"label": "length", "kind": "Length", "data_type": "uint16", "length": 2, "color": "#4361ee"},
    {"label": "data", "kind": "Data", "data_type": "float", "length": 4, "color": "#80ed99"},
    {
        "label": "checksum",
        "kind": "Checksum",
        "data_type": "crc16-xmodem",
        "length": 2,
        "color": "#ffb020",
        "include_in_checksum": False,
    },
    {"label": "tail", "kind": "Tail", "data_type": "hex", "length": 2, "color": "#f72585"},
    {"label": "skip", "kind": "Skip", "data_type": "hex", "length": 1, "color": "#8d99ae", "include_in_checksum": False},
]


class FieldLibraryWidget(QWidget):
    template_clicked = pyqtSignal(dict)
    template_drag_moved = pyqtSignal(dict, QPoint)
    template_drag_finished = pyqtSignal(dict, QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("protocolLibraryPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("Field Library", self)
        title.setObjectName("protocolPanelTitleLabel")
        layout.addWidget(title)

        for template in FIELD_TEMPLATES:
            card = FieldTemplateCard(template, self)
            card.clicked.connect(self.template_clicked)
            card.drag_moved.connect(self.template_drag_moved)
            card.drag_finished.connect(self.template_drag_finished)
            layout.addWidget(card)

        layout.addStretch(1)


class FieldTemplateCard(QWidget):
    clicked = pyqtSignal(dict)
    drag_moved = pyqtSignal(dict, QPoint)
    drag_finished = pyqtSignal(dict, QPoint)

    def __init__(self, template, parent=None):
        super().__init__(parent)
        self.template = dict(template)
        self._press_pos = QPoint()
        self._dragging = False
        self.setObjectName("protocolFieldTemplateButton")
        self.setCursor(Qt.OpenHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 0, 8)
        layout.setSpacing(8)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        title = QLabel(template["kind"], self)
        title.setObjectName("protocolTemplateTitleLabel")
        title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        meta = QLabel(f"{template['data_type']} - {template['length']}B", self)
        meta.setObjectName("protocolTemplateMetaLabel")
        meta.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        text_layout.addWidget(title)
        text_layout.addWidget(meta)
        layout.addLayout(text_layout)
        layout.addStretch(1)

        stripe = QFrame(self)
        stripe.setObjectName("protocolTemplateColorStripe")
        stripe.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        stripe.setFixedWidth(5)
        stripe.setStyleSheet(f"background: {template['color']}; border-radius: 2px;")
        layout.addWidget(stripe)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.pos()
            self._dragging = False
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self._dragging and (event.pos() - self._press_pos).manhattanLength() < DRAG_THRESHOLD:
            return
        self._dragging = True
        self.drag_moved.emit(dict(self.template), event.globalPos())

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        if event.button() == Qt.LeftButton and self._dragging:
            self.drag_finished.emit(dict(self.template), event.globalPos())
            self._dragging = False
            event.accept()
            return
        if event.button() == Qt.LeftButton:
            self.clicked.emit(dict(self.template))
        super().mouseReleaseEvent(event)


class ProtocolNameLabel(QLabel):
    clicked = pyqtSignal(str)
    drag_moved = pyqtSignal(str, QPoint)
    drag_finished = pyqtSignal(str, QPoint)

    def __init__(self, protocol_name, selected=False, parent=None):
        super().__init__(protocol_name, parent)
        self.protocol_name = protocol_name
        self._press_pos = QPoint()
        self._dragging = False
        self.setObjectName("protocolFrameLabel")
        self.setProperty("selected", selected)
        self.setCursor(Qt.OpenHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.pos()
            self._dragging = False
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self._dragging and (event.pos() - self._press_pos).manhattanLength() < DRAG_THRESHOLD:
            return
        self._dragging = True
        self.drag_moved.emit(self.protocol_name, event.globalPos())

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        if event.button() == Qt.LeftButton and self._dragging:
            self.drag_finished.emit(self.protocol_name, event.globalPos())
            self._dragging = False
            event.accept()
            return
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.protocol_name)
        super().mouseReleaseEvent(event)


class ProtocolFieldBlock(QWidget):
    clicked = pyqtSignal(str, str)
    drag_moved = pyqtSignal(str, str, QPoint)
    drag_finished = pyqtSignal(str, str, QPoint)

    def __init__(self, protocol_name, field_item, selected=False, parent=None):
        super().__init__(parent)
        self.protocol_name = protocol_name
        self.field_item = field_item
        self._press_pos = QPoint()
        self._dragging = False
        self.setObjectName("protocolFieldBlock")
        self.setProperty("selected", selected)
        self.setCursor(Qt.OpenHandCursor)
        self._apply_selected_style(selected)
        self._build_ui()

    def _apply_selected_style(self, selected):
        if selected:
            self.setStyleSheet(
                "QWidget#protocolFieldBlock {"
                "background: #22364d;"
                "border: 7px solid #2d8cff;"
                "border-radius: 7px;"
                "min-width: 128px;"
                "}"
            )
            return
        self.setStyleSheet(
            "QWidget#protocolFieldBlock {"
            "background: #2b2b2b;"
            "border: 2px solid transparent;"
            "border-radius: 7px;"
            "min-width: 128px;"
            "}"
        )

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(5)

        color_bar = QFrame(self)
        color_bar.setObjectName("protocolFieldColorBar")
        color_bar.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        color_bar.setFixedHeight(4)
        color_bar.setStyleSheet(f"background: {self.field_item.color}; border-radius: 2px;")
        layout.addWidget(color_bar)

        label = QLabel(self.field_item.label, self)
        label.setObjectName("protocolFieldNameLabel")
        label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(label)

        meta = QLabel(f"{self.field_item.data_type} - {self.field_item.length}B", self)
        meta.setObjectName("protocolFieldMetaLabel")
        meta.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(meta)

        byte_range = QLabel(f"byte {self.field_item.start}..{self.field_item.end}", self)
        byte_range.setObjectName("protocolFieldRangeLabel")
        byte_range.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(byte_range)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.pos()
            self._dragging = False
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self._dragging and (event.pos() - self._press_pos).manhattanLength() < DRAG_THRESHOLD:
            return
        self._dragging = True
        self.drag_moved.emit(self.protocol_name, self.field_item.id, event.globalPos())

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        if event.button() == Qt.LeftButton and self._dragging:
            self.drag_finished.emit(self.protocol_name, self.field_item.id, event.globalPos())
            self._dragging = False
            event.accept()
            return
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.protocol_name, self.field_item.id)
        super().mouseReleaseEvent(event)


class ProtocolFrameWidget(QWidget):
    protocol_drag_moved = pyqtSignal(str, QPoint)
    protocol_drag_finished = pyqtSignal(str, QPoint)
    frame_selected = pyqtSignal(str)
    field_selected = pyqtSignal(str, str)
    field_drag_moved = pyqtSignal(str, str, QPoint)
    field_drag_finished = pyqtSignal(str, str, QPoint)

    def __init__(self, protocol, selected_protocol_name="", selected_field_id="", parent=None):
        super().__init__(parent)
        self.protocol = protocol
        self._field_blocks = []
        self.setObjectName("protocolFrameWidget")
        self.setProperty("selected", protocol.name == selected_protocol_name)
        self._build_ui(selected_protocol_name, selected_field_id)

    def _build_ui(self, selected_protocol_name, selected_field_id):
        frame_layout = QVBoxLayout(self)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        frame_label = ProtocolNameLabel(self.protocol.name, self.protocol.name == selected_protocol_name, self)
        frame_label.clicked.connect(self.frame_selected)
        frame_label.drag_moved.connect(self.protocol_drag_moved)
        frame_label.drag_finished.connect(self.protocol_drag_finished)
        header_layout.addWidget(frame_label)
        header_layout.addStretch(1)
        frame_layout.addLayout(header_layout)

        self.field_row = QHBoxLayout()
        self.field_row.setContentsMargins(0, 0, 0, 0)
        self.field_row.setSpacing(10)
        for field_item in self.protocol.current_frame.fields:
            block = ProtocolFieldBlock(
                self.protocol.name,
                field_item,
                field_item.id == selected_field_id,
                self,
            )
            block.clicked.connect(self.field_selected)
            block.drag_moved.connect(self.field_drag_moved)
            block.drag_finished.connect(self.field_drag_finished)
            self._field_blocks.append(block)
            self.field_row.addWidget(block)

        self.insert_indicator = QFrame(self)
        self.insert_indicator.setObjectName("protocolInsertIndicator")
        self.insert_indicator.setFixedWidth(3)
        self.insert_indicator.hide()
        self.field_row.addWidget(self.insert_indicator)
        self.field_row.addStretch(1)
        frame_layout.addLayout(self.field_row)

    def field_target_index_from_global(self, global_pos):
        return self.field_target_index(self.mapFromGlobal(global_pos))

    def field_target_index(self, local_pos):
        blocks = [block for block in self._field_blocks if block.isVisible()]
        if not blocks:
            return 0
        for index, block in enumerate(blocks):
            if local_pos.x() < block.geometry().center().x():
                return index
        return len(blocks)

    def show_insert_indicator_from_global(self, global_pos):
        self._show_insert_indicator(self.field_target_index_from_global(global_pos))

    def hide_insert_indicator(self):
        self.insert_indicator.hide()

    def _show_insert_indicator(self, index):
        self.field_row.removeWidget(self.insert_indicator)
        index = max(0, min(index, len(self._field_blocks)))
        self.field_row.insertWidget(index, self.insert_indicator)
        self.insert_indicator.show()


class ProtocolCanvasWidget(QWidget):
    protocol_selected = pyqtSignal(str)
    protocol_reorder_requested = pyqtSignal(str, int)
    field_selected = pyqtSignal(str, str)
    field_reorder_requested = pyqtSignal(str, str, int)
    field_template_dropped = pyqtSignal(str, dict, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("protocolCanvasPanel")
        self.protocols = []
        self.current_protocol_name = ""
        self.selected_field_id = ""
        self._frame_widgets = []
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        title = QLabel("Protocol Canvas", self)
        title.setObjectName("protocolPanelTitleLabel")
        root_layout.addWidget(title)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("protocolCanvasScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.content = QWidget(self.scroll_area)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(14)
        self.protocol_insert_indicator = QFrame(self.content)
        self.protocol_insert_indicator.setObjectName("protocolFrameInsertIndicator")
        self.protocol_insert_indicator.setFixedHeight(3)
        self.protocol_insert_indicator.hide()
        self.scroll_area.setWidget(self.content)
        root_layout.addWidget(self.scroll_area)

    def set_protocols(self, protocols, current_protocol_name="", selected_field_id=""):
        self.protocols = list(protocols)
        self.current_protocol_name = current_protocol_name or ""
        self.selected_field_id = selected_field_id or ""
        self._render()

    def handle_template_drag_moved(self, _template, global_pos):
        frame = self._frame_at_global_pos(global_pos)
        self._hide_all_field_indicators(except_frame=frame)
        if frame is not None:
            frame.show_insert_indicator_from_global(global_pos)

    def handle_template_drag_finished(self, template, global_pos):
        frame = self._frame_at_global_pos(global_pos)
        self._hide_all_field_indicators()
        if frame is None:
            return
        target_index = frame.field_target_index_from_global(global_pos)
        self.field_template_dropped.emit(frame.protocol.name, dict(template), target_index)

    def _render(self):
        self._clear_layout(self.content_layout)
        self._frame_widgets = []
        self.protocol_insert_indicator.setParent(self.content)
        self.protocol_insert_indicator.hide()
        if not self.protocols:
            self.content_layout.addStretch(1)
            return

        for protocol in self.protocols:
            frame_widget = ProtocolFrameWidget(
                protocol,
                self.current_protocol_name,
                self.selected_field_id,
                self.content,
            )
            frame_widget.frame_selected.connect(self.protocol_selected)
            frame_widget.protocol_drag_moved.connect(self._handle_protocol_drag_moved)
            frame_widget.protocol_drag_finished.connect(self._handle_protocol_drag_finished)
            frame_widget.field_selected.connect(self.field_selected)
            frame_widget.field_drag_moved.connect(self._handle_field_drag_moved)
            frame_widget.field_drag_finished.connect(self._handle_field_drag_finished)
            self._frame_widgets.append(frame_widget)
            self.content_layout.addWidget(frame_widget)

        self.content_layout.addStretch(1)

    def _handle_protocol_drag_moved(self, _protocol_name, global_pos):
        target_index = self._frame_target_index_from_global(global_pos)
        self._show_protocol_insert_indicator(target_index)

    def _handle_protocol_drag_finished(self, protocol_name, global_pos):
        self.protocol_insert_indicator.hide()
        target_index = self._frame_target_index_from_global(global_pos)
        self.protocol_reorder_requested.emit(protocol_name, target_index)

    def _handle_field_drag_moved(self, protocol_name, _field_id, global_pos):
        frame = self._frame_at_global_pos(global_pos)
        if frame is None or frame.protocol.name != protocol_name:
            self._hide_all_field_indicators()
            return
        self._hide_all_field_indicators(except_frame=frame)
        frame.show_insert_indicator_from_global(global_pos)

    def _handle_field_drag_finished(self, protocol_name, field_id, global_pos):
        frame = self._frame_at_global_pos(global_pos)
        self._hide_all_field_indicators()
        if frame is None or frame.protocol.name != protocol_name:
            return
        target_index = frame.field_target_index_from_global(global_pos)
        self.field_reorder_requested.emit(protocol_name, field_id, target_index)

    def _frame_at_global_pos(self, global_pos):
        local_pos = self.content.mapFromGlobal(global_pos)
        for frame in self._frame_widgets:
            if frame.geometry().contains(local_pos):
                return frame
        return None

    def _frame_target_index_from_global(self, global_pos):
        return self._frame_target_index(self.content.mapFromGlobal(global_pos))

    def _frame_target_index(self, local_pos):
        frames = [frame for frame in self._frame_widgets if frame.isVisible()]
        if not frames:
            return 0
        for index, frame in enumerate(frames):
            if local_pos.y() < frame.geometry().center().y():
                return index
        return len(frames)

    def _show_protocol_insert_indicator(self, index):
        self.content_layout.removeWidget(self.protocol_insert_indicator)
        index = max(0, min(index, len(self._frame_widgets)))
        self.content_layout.insertWidget(index, self.protocol_insert_indicator)
        self.protocol_insert_indicator.show()

    def _hide_all_field_indicators(self, except_frame=None):
        for frame in self._frame_widgets:
            if frame is not except_frame:
                frame.hide_insert_indicator()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None and widget is not self.protocol_insert_indicator:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)


class ProtocolPropertyPanel(QWidget):
    protocol_changed = pyqtSignal(dict)
    field_changed = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("protocolPropertyPanel")
        self._field_id = ""
        self._guard = False
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        title = QLabel("Properties", self)
        title.setObjectName("protocolPanelTitleLabel")
        root_layout.addWidget(title)

        self.stack = QStackedWidget(self)
        root_layout.addWidget(self.stack)
        self._build_protocol_page()
        self._build_field_page()

    def _build_protocol_page(self):
        page = QWidget(self.stack)
        form = QFormLayout(page)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        self.protocol_name_edit = QLineEdit(page)
        self.code_mode_combo = QComboBox(page)
        self.code_mode_combo.addItems(["simple", "full"])
        self.byte_order_combo = QComboBox(page)
        self.byte_order_combo.addItems(["little", "big"])
        self.checksum_combo = QComboBox(page)
        self.checksum_combo.addItems(["none", "sum8", "crc8", "crc16-xmodem"])
        form.addRow("Protocol Name", self.protocol_name_edit)
        form.addRow("Code Mode", self.code_mode_combo)
        form.addRow("Byte Order", self.byte_order_combo)
        form.addRow("Checksum", self.checksum_combo)
        self.stack.addWidget(page)

        self.protocol_name_edit.editingFinished.connect(self._emit_protocol_changed)
        self.code_mode_combo.currentTextChanged.connect(self._emit_protocol_changed)
        self.byte_order_combo.currentTextChanged.connect(self._emit_protocol_changed)
        self.checksum_combo.currentTextChanged.connect(self._emit_protocol_changed)

    def _build_field_page(self):
        page = QWidget(self.stack)
        form = QFormLayout(page)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        self.field_name_edit = QLineEdit(page)
        self.field_kind_combo = QComboBox(page)
        self.field_kind_combo.addItems(["Header", "FrameId", "Length", "Data", "Checksum", "Tail", "Skip"])
        self.field_type_combo = QComboBox(page)
        self.field_type_combo.addItems(["hex", "uint8", "uint16", "uint32", "float", "double", "string", "crc16-xmodem"])
        self.field_length_spin = QSpinBox(page)
        self.field_length_spin.setRange(0, 65535)
        self.field_default_edit = QLineEdit(page)
        self.field_checksum_check = QCheckBox("Include checksum", page)
        self.field_color_edit = QLineEdit(page)
        form.addRow("Field Name", self.field_name_edit)
        form.addRow("Field Kind", self.field_kind_combo)
        form.addRow("Data Type", self.field_type_combo)
        form.addRow("Byte Length", self.field_length_spin)
        form.addRow("Default", self.field_default_edit)
        form.addRow("", self.field_checksum_check)
        form.addRow("Color", self.field_color_edit)
        self.stack.addWidget(page)

        self.field_name_edit.editingFinished.connect(self._emit_field_changed)
        self.field_kind_combo.currentTextChanged.connect(self._emit_field_changed)
        self.field_type_combo.currentTextChanged.connect(self._emit_field_changed)
        self.field_length_spin.valueChanged.connect(self._emit_field_changed)
        self.field_default_edit.editingFinished.connect(self._emit_field_changed)
        self.field_checksum_check.toggled.connect(self._emit_field_changed)
        self.field_color_edit.editingFinished.connect(self._emit_field_changed)

    def show_protocol(self, protocol):
        self._guard = True
        self._field_id = ""
        self.protocol_name_edit.setText(protocol.name)
        self._set_combo_value(self.code_mode_combo, protocol.code_mode)
        self._set_combo_value(self.byte_order_combo, protocol.byte_order)
        self._set_combo_value(self.checksum_combo, protocol.checksum)
        self.stack.setCurrentIndex(0)
        self._guard = False

    def show_field(self, field_item):
        self._guard = True
        self._field_id = field_item.id
        self.field_name_edit.setText(field_item.label)
        self._set_combo_value(self.field_kind_combo, field_item.kind)
        self._set_combo_value(self.field_type_combo, field_item.data_type)
        self.field_length_spin.setValue(field_item.length)
        self.field_default_edit.setText(field_item.default_value)
        self.field_checksum_check.setChecked(field_item.include_in_checksum)
        self.field_color_edit.setText(field_item.color)
        self.stack.setCurrentIndex(1)
        self._guard = False

    def _set_combo_value(self, combo, value):
        if combo.findText(value) < 0:
            combo.addItem(value)
        combo.setCurrentText(value)

    def _emit_protocol_changed(self, *_args):
        if self._guard:
            return
        self.protocol_changed.emit(
            {
                "name": self.protocol_name_edit.text().strip(),
                "code_mode": self.code_mode_combo.currentText(),
                "byte_order": self.byte_order_combo.currentText(),
                "checksum": self.checksum_combo.currentText(),
            }
        )

    def _emit_field_changed(self, *_args):
        if self._guard or not self._field_id:
            return
        self.field_changed.emit(
            self._field_id,
            {
                "label": self.field_name_edit.text().strip(),
                "kind": self.field_kind_combo.currentText(),
                "data_type": self.field_type_combo.currentText(),
                "length": self.field_length_spin.value(),
                "default_value": self.field_default_edit.text(),
                "include_in_checksum": self.field_checksum_check.isChecked(),
                "color": self.field_color_edit.text().strip() or "#2d8cff",
            },
        )
