from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Union


class Defaults:
    MAX_VALUES = 1000000
    SORT_KEYS = False
    STRINGIFY = False
    YAML_STYLE = ""

    INDENT = None
    JSON_INDENT = 4
    PYTHON_INDENT = 1
    YAML_INDENT = 2

    MULTILINE_THRESHOLD = 6

    WIDTH = 80


YAMLStyle = Literal["", "'", '"', "|", ">"]
YAMLVersion = Union[tuple[int, int], None]


@dataclass(frozen=True)
class FormatOptions:
    pass


@dataclass(frozen=True)
class CBOROptions(FormatOptions):
    pass


@dataclass(frozen=True)
class JSONOptions(FormatOptions):
    indent: int | None = Defaults.JSON_INDENT
    sort_keys: bool = Defaults.SORT_KEYS
    stringify: bool = Defaults.STRINGIFY


@dataclass(frozen=True)
class MsgPackOptions(FormatOptions):
    pass


@dataclass(frozen=True)
class PythonOptions(FormatOptions):
    indent: int | None = Defaults.PYTHON_INDENT
    sort_keys: bool = Defaults.SORT_KEYS
    width: int = Defaults.WIDTH


@dataclass(frozen=True)
class TOMLOptions(FormatOptions):
    indent: int | None = Defaults.INDENT
    multiline_threshold: int = Defaults.MULTILINE_THRESHOLD
    sort_keys: bool = Defaults.SORT_KEYS
    stringify: bool = Defaults.STRINGIFY


@dataclass(frozen=True)
class YAMLOptions(FormatOptions):
    expand_aliases: bool = False
    indent: int = Defaults.YAML_INDENT
    style: YAMLStyle = Defaults.YAML_STYLE
    style_newline: YAMLStyle | None = None
    version: YAMLVersion = (1, 2)
    width: int = Defaults.WIDTH
