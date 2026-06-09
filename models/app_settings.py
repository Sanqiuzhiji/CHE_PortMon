# -*- coding: utf-8 -*-
from dataclasses import asdict, dataclass


@dataclass
class AppSettings:
    theme: str = "深色"
    default_baudrate: str = "115200"
    auto_connect: bool = False
    default_save_path: str = ""

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            return cls()
        return cls(
            theme=data.get("theme", cls.theme),
            default_baudrate=str(data.get("default_baudrate", cls.default_baudrate)),
            auto_connect=bool(data.get("auto_connect", cls.auto_connect)),
            default_save_path=data.get("default_save_path", cls.default_save_path),
        )

    def to_dict(self):
        return asdict(self)
