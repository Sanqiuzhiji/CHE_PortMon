# -*- coding: utf-8 -*-
from datetime import datetime


def text_to_bytes(text, append_newline=False, encoding="utf-8"):
    if append_newline:
        text += "\n"
    return text.encode(encoding)


def hex_to_bytes(hex_text):
    cleaned = "".join(hex_text.split())
    if not cleaned:
        return b""
    if len(cleaned) % 2:
        raise ValueError("HEX length must be even")
    return bytes.fromhex(cleaned)


def bytes_to_hex(data):
    raw = bytes(data)
    return " ".join(f"{byte:02X}" for byte in raw)


def bytes_to_hex_keep_newlines(data):
    raw = bytes(data)
    parts = []
    hex_run = bytearray()
    index = 0
    while index < len(raw):
        byte = raw[index]
        if byte in (10, 13):
            if hex_run:
                parts.append(bytes_to_hex(hex_run))
                hex_run.clear()
            if byte == 13 and index + 1 < len(raw) and raw[index + 1] == 10:
                parts.append("\r\n")
                index += 2
                continue
            parts.append(chr(byte))
        else:
            hex_run.append(byte)
        index += 1
    if hex_run:
        parts.append(bytes_to_hex(hex_run))
    return "".join(parts)


def current_timestamp():
    return datetime.now().strftime("[%H:%M:%S] ")


def format_received_data(data, hex_display=False, timestamp=False):
    if hex_display:
        text = bytes_to_hex(data)
    else:
        text = bytes(data).decode("utf-8", errors="ignore")

    if timestamp:
        return current_timestamp() + text
    return text
