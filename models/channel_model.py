from dataclasses import dataclass


DEFAULT_CHANNEL_COLORS = [
    "#6c7cff",
    "#ff3b30",
    "#31d843",
    "#ffb000",
    "#bb00ff",
    "#00a6a6",
    "#5c6cff",
    "#ff5c64",
    "#6b747c",
    "#ff0080",
]


@dataclass
class ChannelState:
    index: int
    key: str
    name: str
    color: str
    raw_value: float = 0.0
    gain: float = 1.0
    offset: float = 0.0
    enabled: bool = True

    @property
    def display_value(self):
        return self.raw_value * self.gain + self.offset
