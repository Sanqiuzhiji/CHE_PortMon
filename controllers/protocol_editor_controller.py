# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from models.protocol_model import ProtocolField
from services.protocol_codegen_service import ProtocolCodegenService
from services.protocol_service import ProtocolService


class ProtocolEditorController:
    def __init__(self, page, service=None, codegen_service=None):
        self.page = page
        self.service = service or ProtocolService()
        self.codegen_service = codegen_service or ProtocolCodegenService()
        self.protocols = []
        self.current_protocol = None
        self.current_protocol_name = ""
        self.selected_field_id = ""

        self._connect_signals()
        self.refresh_protocols()

    def _connect_signals(self):
        self.page.refresh_requested.connect(self.refresh_protocols)
        self.page.new_requested.connect(self.new_protocol)
        self.page.duplicate_requested.connect(self.duplicate_protocol)
        self.page.delete_requested.connect(self.delete_protocol)
        self.page.delete_field_requested.connect(self.delete_current_field)
        self.page.import_requested.connect(self.import_protocol)
        self.page.export_requested.connect(self.export_protocol)
        self.page.save_requested.connect(self.save_protocol)
        self.page.generate_code_requested.connect(self.generate_code)
        self.page.test_parse_requested.connect(self.generate_code)
        self.page.protocol_selected.connect(self.load_protocol)
        self.page.canvas.protocol_selected.connect(self.select_protocol)
        self.page.canvas.protocol_reorder_requested.connect(self.reorder_protocol)
        self.page.canvas.field_selected.connect(self.select_field)
        self.page.canvas.field_reorder_requested.connect(self.reorder_field)
        self.page.canvas.field_template_dropped.connect(self.add_field_to_protocol_at)
        self.page.property_panel.protocol_changed.connect(self.update_protocol_properties)
        self.page.property_panel.field_changed.connect(self.update_field_properties)

    def refresh_protocols(self):
        names = self.service.list_protocols()
        self.protocols = []
        for name in names:
            try:
                self.protocols.append(self.service.load_protocol(name))
            except Exception:
                continue
        current = self.current_protocol.name if self.current_protocol is not None else (names[0] if names else "")
        self.page.set_protocol_names(names, current)
        if current:
            self.load_protocol(current)
        else:
            self._refresh_view()

    def load_protocol(self, name):
        if not name:
            return
        try:
            self.current_protocol = self._protocol_by_name(name) or self.service.load_protocol(name)
        except Exception as exc:
            QMessageBox.warning(self.page, "Protocol Editor", f"Failed to load protocol: {exc}")
            return
        self.current_protocol_name = self.current_protocol.name
        self.selected_field_id = ""
        self._refresh_view()

    def select_protocol(self, name):
        protocol = self._protocol_by_name(name)
        if protocol is None:
            return
        self.current_protocol = protocol
        self.current_protocol_name = protocol.name
        self.selected_field_id = ""
        self.page.set_protocol_names([item.name for item in self.protocols], protocol.name)
        self._refresh_view()

    def new_protocol(self):
        self.current_protocol = self.service.new_protocol()
        self.protocols.append(self.current_protocol)
        self.current_protocol_name = self.current_protocol.name
        self.selected_field_id = ""
        self.refresh_protocols()

    def duplicate_protocol(self):
        if self.current_protocol is None:
            return
        self.current_protocol = self.service.duplicate_protocol(self.current_protocol)
        self.protocols.append(self.current_protocol)
        self.current_protocol_name = self.current_protocol.name
        self.selected_field_id = ""
        self.refresh_protocols()

    def delete_protocol(self):
        if self.current_protocol is None:
            return
        self.service.delete_protocol(self.current_protocol.name)
        self.protocols = [item for item in self.protocols if item.name != self.current_protocol.name]
        self.current_protocol = None
        self.current_protocol_name = ""
        self.selected_field_id = ""
        self.refresh_protocols()

    def import_protocol(self):
        path, _ = QFileDialog.getOpenFileName(
            self.page,
            "Import protocol",
            "",
            "Protocol JSON (*.json);;All Files (*)",
        )
        if not path:
            return
        try:
            self.current_protocol = self.service.import_protocol(path)
            self.protocols.append(self.current_protocol)
            self.current_protocol_name = self.current_protocol.name
            self.selected_field_id = ""
            self.refresh_protocols()
        except Exception as exc:
            QMessageBox.warning(self.page, "Protocol Editor", f"Failed to import protocol: {exc}")

    def export_protocol(self):
        if self.current_protocol is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self.page,
            "Export protocol",
            f"{self.current_protocol.name}.json",
            "Protocol JSON (*.json);;All Files (*)",
        )
        if not path:
            return
        try:
            self.service.export_protocol(self.current_protocol, path)
        except Exception as exc:
            QMessageBox.warning(self.page, "Protocol Editor", f"Failed to export protocol: {exc}")

    def save_protocol(self):
        if self.current_protocol is None:
            return
        old_name = self.current_protocol_name
        self.current_protocol.recalculate_ranges()
        try:
            self.service.save_protocol(self.current_protocol)
            if old_name and old_name != self.current_protocol.name:
                self.service.delete_protocol(old_name)
            self.current_protocol_name = self.current_protocol.name
            self.page.set_protocol_names(self.service.list_protocols(), self.current_protocol.name)
            self._sync_current_protocol_in_list()
            self._refresh_view()
        except Exception as exc:
            QMessageBox.warning(self.page, "Protocol Editor", f"Failed to save protocol: {exc}")

    def generate_code(self):
        if self.current_protocol is None:
            return
        code = self.codegen_service.generate_parser(self.current_protocol)
        self.page.show_generated_code(code)

    def add_field_from_template(self, template):
        if self.current_protocol is None:
            self.new_protocol()
        self.current_protocol_name = self.current_protocol.name
        self._add_field_to_protocol(self.current_protocol, template, len(self.current_protocol.current_frame.fields))

    def add_field_to_protocol_at(self, protocol_name, template, target_index):
        protocol = self._protocol_by_name(protocol_name)
        if protocol is None:
            return
        self.current_protocol = protocol
        self.current_protocol_name = protocol.name
        self.page.set_protocol_names([item.name for item in self.protocols], protocol.name)
        self._add_field_to_protocol(protocol, template, target_index)

    def _add_field_to_protocol(self, protocol, template, target_index):
        field_item = ProtocolField(
            label=self._unique_field_label(protocol, template.get("label", "field")),
            kind=template.get("kind", "Data"),
            data_type=template.get("data_type", "hex"),
            length=int(template.get("length", 1)),
            color=template.get("color", "#2d8cff"),
            include_in_checksum=bool(template.get("include_in_checksum", True)),
        )
        fields = protocol.current_frame.fields
        target_index = max(0, min(len(fields), target_index))
        fields.insert(target_index, field_item)
        self.selected_field_id = field_item.id
        self._refresh_view()

    def select_field(self, protocol_name, field_id):
        protocol = self._protocol_by_name(protocol_name)
        if protocol is not None:
            self.current_protocol = protocol
            self.current_protocol_name = protocol.name
            self.page.set_protocol_names([item.name for item in self.protocols], protocol.name)
        self.selected_field_id = field_id
        self._refresh_view()

    def update_protocol_properties(self, values):
        if self.current_protocol is None:
            return
        name = values.get("name") or self.current_protocol.name
        self.current_protocol.name = name
        self.current_protocol.code_mode = values.get("code_mode", self.current_protocol.code_mode)
        self.current_protocol.byte_order = values.get("byte_order", self.current_protocol.byte_order)
        self.current_protocol.checksum = values.get("checksum", self.current_protocol.checksum)
        self.current_protocol.current_frame.name = name
        self._refresh_view()

    def update_field_properties(self, field_id, values):
        field_item = self._field_by_id(field_id)
        if field_item is None:
            return
        field_item.label = values.get("label") or field_item.label
        field_item.kind = values.get("kind", field_item.kind)
        field_item.data_type = values.get("data_type", field_item.data_type)
        field_item.length = max(0, int(values.get("length", field_item.length)))
        field_item.default_value = values.get("default_value", field_item.default_value)
        field_item.include_in_checksum = bool(values.get("include_in_checksum", field_item.include_in_checksum))
        field_item.color = values.get("color") or field_item.color
        self._refresh_view()

    def delete_current_field(self):
        if self.current_protocol is None or not self.selected_field_id:
            return
        frame = self.current_protocol.current_frame
        before_count = len(frame.fields)
        frame.fields = [item for item in frame.fields if item.id != self.selected_field_id]
        if len(frame.fields) != before_count:
            self.selected_field_id = ""
            self._refresh_view()

    def reorder_protocol(self, protocol_name, target_index):
        index = next((idx for idx, item in enumerate(self.protocols) if item.name == protocol_name), -1)
        if index < 0:
            return
        original_count = len(self.protocols)
        target_index = max(0, min(original_count, target_index))
        protocol = self.protocols.pop(index)
        if index < target_index < original_count:
            target_index -= 1
        target_index = max(0, min(len(self.protocols), target_index))
        if target_index == index:
            self.protocols.insert(index, protocol)
            return
        self.protocols.insert(target_index, protocol)
        self.current_protocol = protocol
        self.current_protocol_name = protocol.name
        self.page.set_protocol_names([item.name for item in self.protocols], protocol.name)
        self._refresh_view()

    def reorder_field(self, protocol_name, field_id, target_index):
        protocol = self._protocol_by_name(protocol_name)
        frame = protocol.current_frame if protocol is not None else None
        if frame is None:
            return
        index = next((idx for idx, item in enumerate(frame.fields) if item.id == field_id), -1)
        if index < 0:
            return
        original_count = len(frame.fields)
        target_index = max(0, min(original_count, target_index))
        field_item = frame.fields.pop(index)
        if index < target_index < original_count:
            target_index -= 1
        target_index = max(0, min(len(frame.fields), target_index))
        if target_index == index:
            frame.fields.insert(index, field_item)
            return
        frame.fields.insert(target_index, field_item)
        self.current_protocol = protocol
        self.current_protocol_name = protocol.name
        self.selected_field_id = field_id
        self.page.set_protocol_names([item.name for item in self.protocols], protocol.name)
        self._refresh_view()

    def _refresh_view(self):
        if self.current_protocol is None:
            return
        for protocol in self.protocols:
            protocol.recalculate_ranges()
        if self.current_protocol is not None:
            self.current_protocol.recalculate_ranges()
        self.page.canvas.set_protocols(self.protocols, self.current_protocol.name, self.selected_field_id)
        field_item = self._field_by_id(self.selected_field_id)
        if field_item is None:
            self.page.property_panel.show_protocol(self.current_protocol)
        else:
            self.page.property_panel.show_field(field_item)

    def _field_by_id(self, field_id):
        if not field_id:
            return None
        protocols = [self.current_protocol] if self.current_protocol is not None else []
        protocols.extend(item for item in self.protocols if item is not self.current_protocol)
        for protocol in protocols:
            if protocol is None:
                continue
            for field_item in protocol.current_frame.fields:
                if field_item.id == field_id:
                    return field_item
        return None

    def _protocol_by_name(self, name):
        for protocol in self.protocols:
            if protocol.name == name:
                return protocol
        return None

    def _sync_current_protocol_in_list(self):
        if self.current_protocol is None:
            return
        for index, protocol in enumerate(self.protocols):
            if protocol.name == self.current_protocol_name or protocol is self.current_protocol:
                self.protocols[index] = self.current_protocol
                return
        self.protocols.append(self.current_protocol)

    def _unique_field_label(self, protocol, base_label):
        existing = {field_item.label for field_item in protocol.current_frame.fields}
        if base_label not in existing:
            return base_label
        index = 2
        while f"{base_label}{index}" in existing:
            index += 1
        return f"{base_label}{index}"
