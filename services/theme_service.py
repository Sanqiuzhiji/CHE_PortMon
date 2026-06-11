# -*- coding: utf-8 -*-
from pathlib import Path

from models.app_settings import normalize_theme


class ThemeService:
    def __init__(self, styles_dir=None):
        self.styles_dir = Path(styles_dir) if styles_dir else Path(__file__).resolve().parents[1] / "ui" / "styles"

    def normalize_theme(self, theme_name):
        return normalize_theme(theme_name)

    def load_stylesheet(self, theme_name):
        theme = self.normalize_theme(theme_name)
        style_path = self.styles_dir / f"{theme}.qss"
        try:
            return style_path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"Theme stylesheet not available: {style_path} ({exc})")
            return ""

    def apply_theme(self, target, theme_name):
        theme = self.normalize_theme(theme_name)
        target.setStyleSheet(self.load_stylesheet(theme))
        return theme
