# -*- coding: utf-8 -*-


class ProtocolCodegenService:
    def generate_parser(self, protocol):
        protocol.recalculate_ranges()
        frame = protocol.current_frame
        endian = "<" if protocol.byte_order == "小端" else ">"
        lines = ["import struct", "", "", "def parse_packet(data: bytes):"]
        result_keys = []

        for field_item in frame.fields:
            name = self._safe_identifier(field_item.label)
            start = field_item.start
            stop = field_item.end + 1
            unpack_format = self._struct_format(field_item.data_type, endian)
            if unpack_format:
                lines.append(f"    {name} = struct.unpack('{unpack_format}', data[{start}:{stop}])[0]")
            else:
                lines.append(f"    {name} = data[{start}:{stop}]")
            result_keys.append((field_item.label, name))

        lines.append("    return {")
        for label, name in result_keys:
            lines.append(f'        "{label}": {name},')
        lines.append("    }")
        return "\n".join(lines)

    def _struct_format(self, data_type, endian):
        formats = {
            "uint8": "B",
            "uint16": "H",
            "uint32": "I",
            "float": "f",
            "double": "d",
        }
        fmt = formats.get(data_type)
        if fmt is None:
            return ""
        return f"{endian}{fmt}"

    def _safe_identifier(self, label):
        result = []
        for char in label:
            if char.isalnum() or char == "_":
                result.append(char)
            else:
                result.append("_")
        value = "".join(result).strip("_") or "field"
        if value[0].isdigit():
            value = f"field_{value}"
        return value
