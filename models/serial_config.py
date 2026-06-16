# -*- coding: utf-8 -*-
from dataclasses import dataclass

from PyQt5.QtSerialPort import QSerialPort


@dataclass
class SerialConfig:
    port_name: str = ""
    baud_rate: int = 115200
    parity: QSerialPort.Parity = QSerialPort.NoParity
    data_bits: QSerialPort.DataBits = QSerialPort.Data8
    stop_bits: QSerialPort.StopBits = QSerialPort.OneStop
    rts: bool = False
    dtr: bool = False


@dataclass
class SendOptions:
    hex_mode: bool = False
    append_newline: bool = False
    auto_interval_ms: int = 1000


@dataclass
class ReceiveOptions:
    hex_display: bool = False
    timestamp: bool = False
    auto_scroll: bool = True
    paused: bool = False
