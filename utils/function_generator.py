# -*- coding: utf-8 -*-
import math

import numpy as np


def generate_sine(x_values, amplitude=1.0, frequency=1.0):
    return amplitude * np.sin(2 * np.pi * frequency * x_values)


def generate_cosine(x_values, amplitude=1.0, frequency=1.0):
    return amplitude * np.cos(2 * np.pi * frequency * x_values)


def generate_tangent(x_values, amplitude=1.0, frequency=1.0):
    values = amplitude * np.tan(2 * np.pi * frequency * x_values)
    return np.clip(values, -10 * amplitude, 10 * amplitude)


def generate_square(x_values, amplitude=1.0, frequency=1.0):
    return amplitude * np.sign(np.sin(2 * np.pi * frequency * x_values))


def generate_triangle(x_values, amplitude=1.0, frequency=1.0):
    phase = (x_values * frequency) % 1
    return amplitude * (2 * np.abs(2 * phase - 1) - 1)


def generate_sawtooth(x_values, amplitude=1.0, frequency=1.0):
    phase = (x_values * frequency) % 1
    return amplitude * (2 * phase - 1)


def generate_exp(x_values, amplitude=1.0, frequency=1.0):
    return amplitude * np.exp(frequency * x_values)


def generate_log(x_values, amplitude=1.0, frequency=1.0):
    with np.errstate(divide="ignore", invalid="ignore"):
        values = amplitude * np.log(frequency * np.abs(x_values) + 1e-10)
        return np.nan_to_num(values, nan=-10 * amplitude, posinf=10 * amplitude, neginf=-10 * amplitude)


FUNCTIONS = {
    "正弦": generate_sine,
    "余弦": generate_cosine,
    "正切": generate_tangent,
    "方波": generate_square,
    "三角波": generate_triangle,
    "锯齿波": generate_sawtooth,
    "指数": generate_exp,
    "对数": generate_log,
}


def generate_function_points(function_name, start, end, step, amplitude, frequency):
    if step <= 0:
        raise ValueError("步长必须大于 0")
    if start >= end:
        raise ValueError("起始值必须小于终止值")

    x_values = np.arange(start, end + step / 2, step, dtype=float)
    generator = FUNCTIONS.get(function_name)
    if generator is None:
        raise ValueError(f"不支持的函数类型: {function_name}")
    y_values = generator(x_values, amplitude, frequency)
    return [(float(x), float(y)) for x, y in zip(x_values, y_values) if math.isfinite(float(y))]
