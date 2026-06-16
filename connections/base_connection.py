# -*- coding: utf-8 -*-
class BaseConnection:
    """Common protocol interface for connection implementations."""

    def connect(self, config=None):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def send(self, data):
        raise NotImplementedError

    def receive(self):
        raise NotImplementedError
