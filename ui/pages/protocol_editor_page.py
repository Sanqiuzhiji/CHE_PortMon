# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QPlainTextEdit, QVBoxLayout, QWidget

from ui.generated.protocol_editor_page_ui import Ui_ProtocolEditorPage
from ui.widgets.protocol_editor_widgets import FieldLibraryWidget, ProtocolCanvasWidget, ProtocolPropertyPanel


class ProtocolEditorPage(QWidget):
    refresh_requested = pyqtSignal()
    new_requested = pyqtSignal()
    duplicate_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    delete_field_requested = pyqtSignal()
    import_requested = pyqtSignal()
    export_requested = pyqtSignal()
    save_requested = pyqtSignal()
    generate_code_requested = pyqtSignal()
    test_parse_requested = pyqtSignal()
    protocol_selected = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.ui = Ui_ProtocolEditorPage()
        self.ui.setupUi(self)

        self.field_library = FieldLibraryWidget(self.ui.libraryContainer)
        self.canvas = ProtocolCanvasWidget(self.ui.canvasContainer)
        self.property_panel = ProtocolPropertyPanel(self.ui.propertyContainer)
        self._install_widget(self.ui.libraryContainer, self.field_library)
        self._install_widget(self.ui.canvasContainer, self.canvas)
        self._install_widget(self.ui.propertyContainer, self.property_panel)
        self._connect_signals()

    def _install_widget(self, container, widget):
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)

    def _connect_signals(self):
        self.ui.refreshButton.clicked.connect(self.refresh_requested)
        self.ui.newButton.clicked.connect(self.new_requested)
        self.ui.duplicateButton.clicked.connect(self.duplicate_requested)
        self.ui.deleteButton.clicked.connect(self.delete_requested)
        self.ui.deleteFieldButton.clicked.connect(self.delete_field_requested)
        self.ui.importButton.clicked.connect(self.import_requested)
        self.ui.exportButton.clicked.connect(self.export_requested)
        self.ui.saveButton.clicked.connect(self.save_requested)
        self.ui.generateButton.clicked.connect(self.generate_code_requested)
        self.ui.testButton.clicked.connect(self.test_parse_requested)
        self.ui.protocolComboBox.currentTextChanged.connect(self.protocol_selected)
        self.field_library.template_drag_moved.connect(self.canvas.handle_template_drag_moved)
        self.field_library.template_drag_finished.connect(self.canvas.handle_template_drag_finished)

    def set_protocol_names(self, names, current_name=""):
        self.ui.protocolComboBox.blockSignals(True)
        self.ui.protocolComboBox.clear()
        self.ui.protocolComboBox.addItems(names)
        if current_name:
            self.ui.protocolComboBox.setCurrentText(current_name)
        self.ui.protocolComboBox.blockSignals(False)

    def show_generated_code(self, code):
        dialog = QDialog(self)
        dialog.setWindowTitle("Generated Parser Code")
        dialog.resize(760, 520)
        layout = QVBoxLayout(dialog)
        editor = QPlainTextEdit(dialog)
        editor.setPlainText(code)
        editor.setReadOnly(True)
        layout.addWidget(editor)
        dialog.exec_()
