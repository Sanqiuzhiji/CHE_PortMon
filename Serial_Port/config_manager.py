# config_manager.py
import json
import os
from typing import Dict, Any

from PyQt5.QtSerialPort import QSerialPortInfo


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
                    {"value": "N", "text": "无", "is_custom": False},
                    {"value": "O", "text": "奇校验", "is_custom": False},
                    {"value": "E", "text": "偶校验", "is_custom": False}
                ],
                "databits": [
                    {"value": 8, "text": "8", "is_custom": False},
                    {"value": 7, "text": "7", "is_custom": False},
                    {"value": 6, "text": "6", "is_custom": False},
                    {"value": 5, "text": "5", "is_custom": False}
                ],
                "stopbits": [
                    {"value": 1, "text": "1", "is_custom": False},
                    {"value": 1.5, "text": "1.5", "is_custom": False},
                    {"value": 2, "text": "2", "is_custom": False}
                ]
            },
            "user_settings": {
                "serial": {
                    "port": "",
                    "baudrate": "115200",
                    "parity": "无",
                    "databits": "8",
                    "stopbits": "1"
                },
                "send": {
                    "hex_send": False,
                    "auto_clear_send": False
                },
                "receive": {
                    "hex_receive": False,
                    "timestamp": False,
                    "auto_clear_receive": False
                },
                "flow_control": {
                    "rts": False,
                    "dtr": False
                },
                "file_paths": {
                    "receive_save": "",
                    "send_file": ""
                }
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
        existing_values = [item["value"] for item in self.config["serial_config"][category]]
        if value in existing_values:
            return False

        new_option = {
            "value": value,
            "text": text,
            "is_custom": True
        }
        self.config["serial_config"][category].append(new_option)
        self.save_config()
        return True

    def save_user_settings(self, settings_dict):
        """保存用户设置"""
        # 更新整个用户设置
        self.config["user_settings"].update(settings_dict)
        self.save_config()

    def load_user_settings(self):
        """加载用户设置"""
        return self.config["user_settings"].copy()

    def save_all_settings(self, serial_app):
        """保存所有设置"""
        all_settings = {
            "serial": {
                "port": serial_app.ui.port_cb.currentText(),
                "baudrate": serial_app.ui.baudrate_cb.currentText(),
                "parity": serial_app.ui.parity_cb.currentText(),
                "databits": serial_app.ui.databits_cb.currentText(),
                "stopbits": serial_app.ui.stopbits_cb.currentText()
            },
            "send": {
                "hex_send": serial_app.ui.hex_send_chb.isChecked(),
                "send_sync": serial_app.ui.send_sync_rbtn.isChecked(),
            },
            "receive": {
                "hex_receive": serial_app.ui.hex_receive_chb.isChecked(),
                "timestamp": serial_app.ui.timestamp_chb.isChecked(),
                "auto_clear_receive": serial_app.ui.auto_clearReceive_chb.isChecked()
            },
            "flow_control": {
                "rts": serial_app.ui.rts_chb.isChecked(),
                "dtr": serial_app.ui.dtr_chb.isChecked()
            },
            "file_paths": {
                "receive_save": serial_app.ui.file_receive_lEdit.text(),
                "send_file": serial_app.ui.file_send_lEdit.text()
            }
        }
        self.save_user_settings(all_settings)

    def is_port_available(self, port_name):
        """检查端口是否可用"""
        if not port_name:
            return False

        available_ports = [port.portName() for port in QSerialPortInfo.availablePorts()]
        return port_name in available_ports

    def get_available_port(self, preferred_port=""):
        """获取可用的端口，优先返回保存的端口"""
        available_ports = [port.portName() for port in QSerialPortInfo.availablePorts()]

        if not available_ports:
            return ""

        # 如果保存的端口可用，优先返回
        if preferred_port and preferred_port in available_ports:
            return preferred_port

        # 否则返回第一个可用端口
        return available_ports[0]