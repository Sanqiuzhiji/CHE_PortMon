# -*- coding: utf-8 -*-
import json
from pathlib import Path

from models.app_settings import AppSettings


class ConfigService:
    def __init__(self, config_path="config/app_settings.json"):
        self.config_path = Path(config_path)

    def load_settings(self):
        if not self.config_path.exists():
            settings = AppSettings()
            self.save_settings(settings)
            return settings
        try:
            settings = AppSettings.from_dict(json.loads(self.config_path.read_text(encoding="utf-8")))
            self.save_settings(settings)
            return settings
        except (OSError, json.JSONDecodeError):
            settings = AppSettings()
            self.save_settings(settings)
            return settings

    def save_settings(self, settings):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(settings.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
