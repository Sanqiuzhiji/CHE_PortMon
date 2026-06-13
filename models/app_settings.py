# -*- coding: utf-8 -*-
from dataclasses import asdict, dataclass


THEME_ALIASES = {
    "dark": "dark",
    "light": "light",
    "夜间模式": "dark",
    "日间模式": "light",
    "深色": "dark",
    "浅色": "light",
    "娣辫壊": "dark",
    "娴呰壊": "light",
}


def normalize_theme(theme):
    return THEME_ALIASES.get(str(theme or "").strip(), "dark")


@dataclass
class AppSettings:
    theme: str = "dark"
    ui_font: str = ""
    default_baudrate: str = "115200"
    auto_connect: bool = False
    default_save_path: str = ""

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            return cls()
        return cls(
            theme=normalize_theme(data.get("theme", cls.theme)),
            ui_font=str(data.get("ui_font", cls.ui_font)).strip(),
            default_baudrate=str(data.get("default_baudrate", cls.default_baudrate)),
            auto_connect=bool(data.get("auto_connect", cls.auto_connect)),
            default_save_path=data.get("default_save_path", cls.default_save_path),
        )

    def to_dict(self):
        self.theme = normalize_theme(self.theme)
        return asdict(self)
