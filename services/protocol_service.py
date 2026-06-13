# -*- coding: utf-8 -*-
import json
import re
import shutil
from pathlib import Path
from uuid import uuid4

from models.protocol_model import ProtocolDefinition, ProtocolField, ProtocolFrame


class ProtocolService:
    def __init__(self, protocols_dir="config/protocols"):
        self.protocols_dir = Path(protocols_dir)
        self.protocols_dir.mkdir(parents=True, exist_ok=True)
        self.ensure_examples()

    def ensure_examples(self):
        for name in ("Test_Protocol", "Test_Protocol2"):
            path = self._path_for_name(name)
            if not path.exists():
                self.save_protocol(self._example_protocol(name))

    def list_protocols(self):
        self.protocols_dir.mkdir(parents=True, exist_ok=True)
        names = []
        for path in sorted(self.protocols_dir.glob("*.json")):
            try:
                names.append(self.load_protocol(path.stem).name)
            except (OSError, json.JSONDecodeError, ValueError):
                names.append(path.stem)
        return sorted(set(names))

    def load_protocol(self, name):
        path = self._path_for_name(name)
        data = json.loads(path.read_text(encoding="utf-8"))
        return ProtocolDefinition.from_dict(data)

    def save_protocol(self, protocol):
        protocol.recalculate_ranges()
        path = self._path_for_name(protocol.name)
        path.write_text(json.dumps(protocol.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def new_protocol(self):
        name = self._unique_name("New_Protocol")
        protocol = ProtocolDefinition(name=name, frames=[ProtocolFrame(name=name)])
        self.save_protocol(protocol)
        return protocol

    def duplicate_protocol(self, protocol):
        data = protocol.to_dict()
        duplicate = ProtocolDefinition.from_dict(data)
        duplicate.name = self._unique_name(f"{protocol.name}_Copy")
        duplicate.current_frame.name = duplicate.name
        for field_item in duplicate.current_frame.fields:
            field_item.id = uuid4().hex
        self.save_protocol(duplicate)
        return duplicate

    def delete_protocol(self, name):
        path = self._path_for_name(name)
        if path.exists():
            path.unlink()

    def import_protocol(self, source_path):
        source = Path(source_path)
        data = json.loads(source.read_text(encoding="utf-8"))
        protocol = ProtocolDefinition.from_dict(data)
        protocol.name = self._unique_name(protocol.name)
        self.save_protocol(protocol)
        return protocol

    def export_protocol(self, protocol, target_path):
        protocol.recalculate_ranges()
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.save_protocol(protocol)
        shutil.copyfile(temp_path, target)
        return target

    def _path_for_name(self, name):
        return self.protocols_dir / f"{self._safe_filename(name)}.json"

    def _safe_filename(self, name):
        safe = re.sub(r"[^0-9A-Za-z_\-]+", "_", name.strip())
        return safe or "protocol"

    def _unique_name(self, base_name):
        existing = set(self.list_protocols())
        if base_name not in existing:
            return base_name
        index = 2
        while f"{base_name}_{index}" in existing:
            index += 1
        return f"{base_name}_{index}"

    def _example_protocol(self, name):
        return ProtocolDefinition(
            name=name,
            code_mode="简洁模式",
            byte_order="小端",
            checksum="crc16-xmodem",
            frames=[
                ProtocolFrame(
                    name=name,
                    fields=[
                        ProtocolField(label="header", kind="Header", data_type="hex", length=2, color="#4cc9f0"),
                        ProtocolField(label="data1", kind="Data", data_type="float", length=4, color="#80ed99"),
                        ProtocolField(
                            label="checksum",
                            kind="Checksum",
                            data_type="crc16-xmodem",
                            length=2,
                            color="#ffb020",
                            include_in_checksum=False,
                        ),
                        ProtocolField(label="tail", kind="Tail", data_type="hex", length=2, color="#f72585"),
                    ],
                )
            ],
        )
