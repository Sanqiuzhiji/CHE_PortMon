# -*- coding: utf-8 -*-
from PyQt5.QtCore import QObject, pyqtSignal

from models.channel_model import ChannelState, DEFAULT_CHANNEL_COLORS


class ChannelManager(QObject):
    channels_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._channels = []
        self._sample_index = 0
        self._sample_interval_s = 0.0002
        self._latest_sample_timestamp_s = 0.0

    def channels(self):
        return list(self._channels)

    def channel_keys(self):
        return [channel.key for channel in self._channels]

    def channel_by_key(self, key):
        for channel in self._channels:
            if channel.key == key:
                return channel
        return None

    def sample_interval_s(self):
        return self._sample_interval_s

    def latest_sample_index(self):
        return max(0, self._sample_index - 1)

    def latest_sample_timestamp_s(self):
        return self._latest_sample_timestamp_s

    def reset_samples(self):
        self._sample_index = 0
        self._latest_sample_timestamp_s = 0.0

    def update_values(self, values, sample_interval_s=None):
        values = list(values or [])
        if sample_interval_s is not None:
            self._sample_interval_s = max(0.000000001, float(sample_interval_s))
        frame_index = self._sample_index
        self._sample_index += 1
        self._latest_sample_timestamp_s = frame_index * self._sample_interval_s
        for index, raw_value in enumerate(values):
            key = f"CH{index}"
            channel = self.channel_by_key(key)
            if channel is None:
                channel = ChannelState(
                    index=index,
                    key=key,
                    name=key,
                    color=DEFAULT_CHANNEL_COLORS[index % len(DEFAULT_CHANNEL_COLORS)],
                    raw_value=float(raw_value),
                )
                self._channels.append(channel)
            channel.index = index
            channel.raw_value = float(raw_value)
            channel.enabled = True
        for index in range(len(values), len(self._channels)):
            self._channels[index].enabled = False
        self.channels_changed.emit(self.channels())

    def update_channel_config(self, key, name=None, color=None, gain=None, offset=None):
        channel = self.channel_by_key(key)
        if channel is None:
            return
        if name is not None:
            channel.name = name
        if color is not None:
            channel.color = color
        if gain is not None:
            channel.gain = float(gain)
        if offset is not None:
            channel.offset = float(offset)
        self.channels_changed.emit(self.channels())
