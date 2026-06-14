# -*- coding: utf-8 -*-

import json
import re
from pathlib import Path


class PlotLayoutService:
    def __init__(self, path=None):
        self.pages_dir = Path("config/plot_pages")

    def load_layout_from(self, path):
        path = Path(path)
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def save_layout(self, layout):
        """
        旧版：保存整个工作区。
        后续如果你要做 Save All，可以继续用这个。
        """
        self.save_layout_to(self.path, layout)

    def save_layout_to(self, path, layout):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as handle:
            json.dump(layout, handle, ensure_ascii=False, indent=2)

    def save_page(self, page_data):
        """
        新版：保存当前 Page。
        根据 page_data['name'] 自动生成文件名。
        如果同名文件已经存在，直接覆盖。
        """
        page_name = page_data.get("name", "Page")
        path = self.page_file_path(page_name)
        self.save_layout_to(path, page_data)
        return path

    def load_page(self, page_name):
        """
        新版：根据 Page 名读取单个 Page。
        """
        path = self.page_file_path(page_name)
        return self.load_layout_from(path)

    def load_all_pages(self):
        """
        新版：启动时读取 config/plot_pages 下所有 Page 文件。
        返回格式仍然保持为：
        {
            "pages": [...]
        }
        这样 PlotPage._load_layout_data(layout) 不需要大改。
        """
        self.pages_dir.mkdir(parents=True, exist_ok=True)

        pages = []
        for path in sorted(self.pages_dir.glob("*.json")):
            try:
                page_data = self.load_layout_from(path)
            except (OSError, ValueError, json.JSONDecodeError):
                continue

            if not isinstance(page_data, dict):
                continue

            if "name" not in page_data:
                page_data["name"] = path.stem

            pages.append(page_data)

        return {"pages": pages}

    def page_file_path(self, page_name):
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        safe_name = self._safe_file_name(page_name)
        return self.pages_dir / f"{safe_name}.json"

    def _safe_file_name(self, name):
        """
        Windows 文件名不能包含 \\ / : * ? " < > |
        Page 名里如果有这些字符，就替换成 _
        """
        name = str(name).strip() or "Page"
        name = re.sub(r'[\\/:*?"<>|]+', "_", name)
        return name
