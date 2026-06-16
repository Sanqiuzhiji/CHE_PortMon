# -*- coding: utf-8 -*-
import struct


class JustFloatParser:
    TAIL_WORD = 0x7F800000

    def __init__(self, endian="<"):
        self.endian = endian
        self.buffer = bytearray()
        self.tail_bytes = struct.pack(f"{endian}I", self.TAIL_WORD)

    def feed(self, data: bytes):
        if data:
            self.buffer.extend(bytes(data))

        frames = []
        tail_len = len(self.tail_bytes)
        search_from = 0
        while True:
            tail_index = self.buffer.find(self.tail_bytes, search_from)
            if tail_index < 0:
                break
            payload = bytes(self.buffer[:tail_index])
            del self.buffer[: tail_index + tail_len]
            search_from = 0
            if not payload:
                continue
            usable_len = len(payload) - (len(payload) % 4)
            if usable_len <= 0:
                continue
            frame = []
            for offset in range(0, usable_len, 4):
                chunk = payload[offset : offset + 4]
                if len(chunk) == 4:
                    frame.append(struct.unpack(f"{self.endian}f", chunk)[0])
            if frame:
                frames.append(frame)
        return frames
