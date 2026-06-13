# -*- coding: utf-8 -*-
import json
from pathlib import Path


class PlotLayoutService:
    def __init__(self, path=None):
        self.path = Path(path or "config/plot_layout.json")

    def ensure_default_layout(self):
        if self.path.exists():
            return self.load_layout()
        layout = {
            "pages": [
                {
                    "name": "Page 1",
                    "controls": [],
                }
            ]
        }
        self.save_layout(layout)
        return layout

    def load_layout(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            return self.ensure_default_layout()
        return self.load_layout_from(self.path)

    def load_layout_from(self, path):
        path = Path(path)
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def save_layout(self, layout):
        self.save_layout_to(self.path, layout)

    def save_layout_to(self, path, layout):
        path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(layout, handle, ensure_ascii=False, indent=2)
