# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class ProtocolField:
    id: str = field(default_factory=lambda: uuid4().hex)
    label: str = "field"
    kind: str = "Data"
    data_type: str = "hex"
    length: int = 1
    start: int = 0
    end: int = 0
    default_value: str = ""
    color: str = "#2d8cff"
    include_in_checksum: bool = True

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get("id") or uuid4().hex,
            label=data.get("label", "field"),
            kind=data.get("kind", "Data"),
            data_type=data.get("data_type", "hex"),
            length=max(0, int(data.get("length", 1))),
            start=max(0, int(data.get("start", 0))),
            end=max(0, int(data.get("end", 0))),
            default_value=data.get("default_value", ""),
            color=data.get("color", "#2d8cff"),
            include_in_checksum=bool(data.get("include_in_checksum", True)),
        )

    def to_dict(self):
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "data_type": self.data_type,
            "length": self.length,
            "start": self.start,
            "end": self.end,
            "default_value": self.default_value,
            "color": self.color,
            "include_in_checksum": self.include_in_checksum,
        }


@dataclass
class ProtocolFrame:
    name: str = "Frame"
    fields: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data):
        frame = cls(
            name=data.get("name", "Frame"),
            fields=[ProtocolField.from_dict(item) for item in data.get("fields", [])],
        )
        frame.recalculate_ranges()
        return frame

    def to_dict(self):
        self.recalculate_ranges()
        return {
            "name": self.name,
            "fields": [field_item.to_dict() for field_item in self.fields],
        }

    def recalculate_ranges(self):
        offset = 0
        for field_item in self.fields:
            field_item.start = offset
            if field_item.length <= 0:
                field_item.end = offset
                continue
            field_item.end = offset + field_item.length - 1
            offset += field_item.length


@dataclass
class ProtocolDefinition:
    name: str = "New_Protocol"
    code_mode: str = "简洁模式"
    byte_order: str = "小端"
    checksum: str = "none"
    frames: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data):
        protocol = cls(
            name=data.get("name", "New_Protocol"),
            code_mode=data.get("code_mode", "简洁模式"),
            byte_order=data.get("byte_order", "小端"),
            checksum=data.get("checksum", "none"),
            frames=[ProtocolFrame.from_dict(item) for item in data.get("frames", [])],
        )
        protocol.ensure_frame()
        protocol.recalculate_ranges()
        return protocol

    def to_dict(self):
        self.recalculate_ranges()
        return {
            "name": self.name,
            "code_mode": self.code_mode,
            "byte_order": self.byte_order,
            "checksum": self.checksum,
            "frames": [frame_item.to_dict() for frame_item in self.frames],
        }

    def ensure_frame(self):
        if not self.frames:
            self.frames.append(ProtocolFrame(name=self.name))

    def recalculate_ranges(self):
        self.ensure_frame()
        for frame_item in self.frames:
            frame_item.recalculate_ranges()

    @property
    def current_frame(self):
        self.ensure_frame()
        return self.frames[0]
