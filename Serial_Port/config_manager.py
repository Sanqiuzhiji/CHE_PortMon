import json
import os
from PyQt5.QtCore import QSettings

class JSONConfigManager:
    def __init__(self, config_file="Serial_Port/config.json"):
        self.config_file = config_file
        self.config = self.load_or_create_config()

    def load_or_create_config(self):
        """加载或创建配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                # 如果文件损坏，创建默认配置
                return self.create_default_config()
        else:
            return self.create_default_config()

    def create_default_config(self):
        """创建默认配置"""
        default_config = {
            "serial_config": {
                "baudrates": [
                    {"value": 9600, "text": "9600", "is_custom": False},
                    {"value": 19200, "text": "19200", "is_custom": False},
                    {"value": 38400, "text": "38400", "is_custom": False},
                    {"value": 57600, "text": "57600", "is_custom": False},
                    {"value": 115200, "text": "115200", "is_custom": False}
                ],
                "parities": [
                    {"value": "N", "text": "无校验", "is_custom": False},
                    {"value": "O", "text": "奇校验", "is_custom": False},
                    {"value": "E", "text": "偶校验", "is_custom": False}
                ],
                "databits": [
                    {"value": 8, "text": "8位", "is_custom": False},
                    {"value": 7, "text": "7位", "is_custom": False},
                    {"value": 6, "text": "6位", "is_custom": False},
                    {"value": 5, "text": "5位", "is_custom": False}
                ],
                "stopbits": [
                    {"value": 1, "text": "1位", "is_custom": False},
                    {"value": 1.5, "text": "1.5位", "is_custom": False},
                    {"value": 2, "text": "2位", "is_custom": False}
                ]
            },
            "user_settings": {
                "last_port": "COM1",
                "last_baudrate": 115200,
                "last_parity": "N",
                "last_databits": 8,
                "last_stopbits": 1
            }
        }

        self.save_config(default_config)
        return default_config

    def save_config(self, config=None):
        """保存配置到文件"""
        if config is None:
            config = self.config

        # 确保目录存在
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def get_config_options(self, category):
        """获取配置选项"""
        return self.config["serial_config"].get(category, [])

    def add_custom_option(self, category, value, text):
        """添加用户自定义选项"""
        # 检查是否已存在
        existing_values = [item["value"] for item in self.config["serial_config"][category]]
        if value in existing_values:
            return False  # 已存在

        # 添加新选项
        new_option = {
            "value": value,
            "text": text,
            "is_custom": True
        }
        self.config["serial_config"][category].append(new_option)
        self.save_config()
        return True

    def remove_custom_option(self, category, value):
        """删除用户自定义选项（只删除自定义的）"""
        options = self.config["serial_config"][category]
        # 只删除自定义的选项
        self.config["serial_config"][category] = [
            item for item in options
            if not (item["value"] == value and item["is_custom"])
        ]
        self.save_config()

    def save_user_settings(self, settings_dict):
        """保存用户最后使用的设置"""
        self.config["user_settings"].update(settings_dict)
        self.save_config()

    def load_user_settings(self):
        """加载用户最后使用的设置"""
        return self.config["user_settings"].copy()