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
        cleaned = "0" + cleaned
    return bytes.fromhex(cleaned)


def bytes_to_hex(data):
    raw = bytes(data)
    return " ".join(f"{byte:02X}" for byte in raw)


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
