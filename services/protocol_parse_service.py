# -*- coding: utf-8 -*-
import struct


class ProtocolParseService:
    def parse_data_fields(self, protocol, payload):
        protocol.recalculate_ranges()
        values = []
        endian = "<" if protocol.byte_order == "小端" else ">"
        for field_item in protocol.current_frame.fields:
            if field_item.kind != "Data":
                continue
            start = field_item.start
            stop = field_item.end + 1
            if len(payload) < stop:
                values.append((field_item.label, "<incomplete>"))
                continue
            raw = payload[start:stop]
            values.append((field_item.label, self._decode_field(field_item.data_type, raw, endian)))
        return values

    def _decode_field(self, data_type, raw, endian):
        formats = {
            "uint8": "B",
            "uint16": "H",
            "uint32": "I",
            "float": "f",
            "double": "d",
        }
        fmt = formats.get(data_type)
        if fmt is None:
            if data_type == "string":
                return raw.decode("utf-8", errors="replace")
            return raw.hex(" ").upper()
        try:
            return struct.unpack(f"{endian}{fmt}", raw)[0]
        except struct.error:
            return raw.hex(" ").upper()
