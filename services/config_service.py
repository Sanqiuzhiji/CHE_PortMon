# -*- coding: utf-8 -*-
import json
from pathlib import Path

from models.app_settings import AppSettings


class ConfigService:
    def __init__(self, config_path="config/app_settings.json"):
        self.config_path = Path(config_path)

    def load_settings(self):
        if not self.config_path.exists():
            return AppSettings()
        try:
            return AppSettings.from_dict(json.loads(self.config_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            return AppSettings()

    def save_settings(self, settings):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(settings.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
