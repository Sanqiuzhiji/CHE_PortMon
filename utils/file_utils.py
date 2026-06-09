# -*- coding: utf-8 -*-


def save_text_file(path, text):
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


def read_binary_file(path):
    with open(path, "rb") as file:
        return file.read()
