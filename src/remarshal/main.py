#! /usr/bin/env python3
# Remarshal, a utility to convert between serialization formats.
# Copyright (c) 2014-2020, 2024 D. Bohdan
# License: MIT

from __future__ import annotations

import argparse
import datetime
import importlib.metadata
import json
import pprint
import re
import sys
import traceback
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Literal,
    Mapping,
    Sequence,
    Union,
    cast,
)

import cbor2  # type: ignore
import colorama
import tomlkit
from rich_argparse import RichHelpFormatter

try:
    import tomllib  # type: ignore
except ModuleNotFoundError:
    import tomli as tomllib

import ruamel.yaml
import ruamel.yaml.parser
import ruamel.yaml.representer
import ruamel.yaml.scanner
import umsgpack

if TYPE_CHECKING:
    from rich.style import StyleType

    YAMLStyle = Literal["", "'", '"', "|", ">"]


class CLIDefaults:
    INDENT = None
    SORT_KEYS = False
    STRINGIFY = False
    WIDTH = 80


class Defaults:
    JSON_INDENT = 4
    MAX_VALUES = 1000000
    YAML_INDENT = 2
    YAML_STYLE = ""


@dataclass(frozen=True)
class FormatOptions:
    pass


@dataclass(frozen=True)
class YAMLOptions(FormatOptions):
    style: YAMLStyle = Defaults.YAML_STYLE


__all__ = [
    "INPUT_FORMATS",
    "OUTPUT_FORMATS",
    "RICH_ARGPARSE_STYLES",
    "CLIDefaults",
    "Defaults",
    "Document",
    "FormatOptions",
    "TooManyValuesError",
    "YAMLOptions",
    "decode",
    "encode",
    "identity",
    "main",
    "remarshal",
    "traverse",
]


INPUT_FORMATS = ["cbor", "json", "msgpack", "toml", "yaml"]
OUTPUT_FORMATS = ["cbor", "json", "msgpack", "python", "toml", "yaml"]
UTF_8 = "utf-8"

RICH_ARGPARSE_STYLES: dict[str, StyleType] = {
    "argparse.args": "green",
    "argparse.groups": "default",
    "argparse.help": "default",
    "argparse.metavar": "green",
    "argparse.prog": "default",
    "argparse.syntax": "bold",
    "argparse.text": "default",
    "argparse.default": "default",
}


# === CLI ===


def _argv0_to_format(argv0: str) -> tuple[str, str]:
    possible_input_format = "(" + "|".join(INPUT_FORMATS) + ")"
    possible_output_format = "(" + "|".join(OUTPUT_FORMATS) + ")"
    match = re.search("^" + possible_input_format + "2" + possible_output_format, argv0)
    from_, to = match.groups() if match else ("", "")
    return from_, to


def _extension_to_format(path: str, formats: list[str]) -> str:
    ext = Path(path).suffix[1:]

    if ext == "py":
        return "python"
    if ext == "yml":
        return "yaml"

    return ext if ext in formats else ""


def _parse_command_line(argv: Sequence[str]) -> argparse.Namespace:
    me = Path(argv[0]).name
    argv0_from, argv0_to = _argv0_to_format(me)
    format_from_argv0 = argv0_to != ""

    RichHelpFormatter.group_name_formatter = lambda x: x
    RichHelpFormatter.styles = RICH_ARGPARSE_STYLES

    parser = argparse.ArgumentParser(
        description="Convert between CBOR, JSON, MessagePack, TOML, and YAML.",
        formatter_class=RichHelpFormatter,
        prog="remarshal",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=importlib.metadata.version("remarshal"),
    )

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("input", default="-", nargs="?", help="input file")
    input_group.add_argument(
        "-i",
        "--input",
        default=None,
        dest="input_flag",
        metavar="<input>",
        help="input file",
    )

    if not format_from_argv0:
        parser.add_argument(
            "--if",
            "--input-format",
            "-f",
            "--from",
            choices=INPUT_FORMATS,
            default="",
            dest="input_format",
            help="input format",
        )

        parser.add_argument(
            "-if",
            choices=INPUT_FORMATS,
            default="",
            dest="input_format",
            help=argparse.SUPPRESS,
        )

    parser.add_argument(
        "--indent",
        default=CLIDefaults.INDENT,
        metavar="<n>",
        type=int,
        help="JSON and YAML indentation",
    )

    parser.add_argument(
        "--indent-json",
        dest="indent",
        type=int,
        help=argparse.SUPPRESS,
    )

    parser.add_argument(
        "--json-indent",
        dest="indent",
        type=int,
        help=argparse.SUPPRESS,
    )

    parser.add_argument(
        "-k",
        "--stringify",
        action="store_true",
        help=(
            "turn into strings: boolean and null keys and date-time keys "
            "and values for JSON; boolean, date-time, and null keys and "
            "null values for TOML"
        ),
    )

    parser.add_argument(
        "--max-values",
        default=Defaults.MAX_VALUES,
        metavar="<n>",
        type=int,
        help=(
            "maximum number of values in input data (default %(default)s, "
            "negative for unlimited)"
        ),
    )

    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("output", default="-", nargs="?", help="output file")
    output_group.add_argument(
        "-o",
        "--output",
        default=None,
        dest="output_flag",
        metavar="<output>",
        help="output file",
    )

    if not format_from_argv0:
        parser.add_argument(
            "--of",
            "--output-format",
            "-t",
            "--to",
            choices=OUTPUT_FORMATS,
            default="",
            dest="output_format",
            help="output format",
        )

        parser.add_argument(
            "-of",
            choices=OUTPUT_FORMATS,
            default="",
            dest="output_format",
            help=argparse.SUPPRESS,
        )

    parser.add_argument(
        "-p",
        "--preserve-key-order",
        help=argparse.SUPPRESS,
    )

    parser.add_argument(
        "-s",
        "--sort-keys",
        action="store_true",
        help="sort JSON, Python, and TOML keys instead of preserving key order",
    )

    parser.add_argument(
        "--unwrap",
        default=None,
        metavar="<key>",
        help="only output the data stored under the given key",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print debug information when an error occurs",
    )

    def output_width(value: str) -> int:
        # This is theoretically compatible with LibYAML.
        return (1 << 32) - 1 if value.lower() == "inf" else int(value)

    parser.add_argument(
        "--width",
        default=CLIDefaults.WIDTH,
        metavar="<n>",
        type=output_width,  # Allow "inf".
        help=(
            "Python line width and YAML line width for long strings"
            " (integer or 'inf')"
        ),
    )

    parser.add_argument(
        "--wrap",
        default=None,
        metavar="<key>",
        help="wrap the data in a map type with the given key",
    )

    parser.add_argument(
        "--yaml-indent",
        dest="indent",
        type=int,
        help=argparse.SUPPRESS,
    )

    parser.add_argument(
        "--yaml-style",
        choices=["", "'", '"', "|", ">"],
        default=YAMLOptions().style,
        help="YAML formatting style",
    )

    parser.add_argument(
        "--yaml-width",
        dest="width",
        type=output_width,
        help=argparse.SUPPRESS,
    )

    colorama.init()
    args = parser.parse_args(args=argv[1:])

    # Use the positional input and output arguments.
    if args.input_flag is not None:
        args.input = args.input_flag

    if args.output_flag is not None:
        args.output = args.output_flag

    # Determine the implicit input and output format if possible.
    if format_from_argv0:
        args.input_format = argv0_from
        args.output_format = argv0_to
    else:
        if args.input_format == "":
            args.input_format = _extension_to_format(args.input, INPUT_FORMATS)
            if args.input_format == "":
                parser.error("Need an explicit input format")

        if args.output_format == "":
            args.output_format = _extension_to_format(args.output, OUTPUT_FORMATS)
            if args.output_format == "":
                parser.error("Need an explicit output format")

    # Replace `yaml_*` options with `YAMLOptions`.
    vars(args)["yaml_options"] = YAMLOptions(
        style=args.yaml_style,
    )

    del vars(args)["yaml_style"]

    return args


# === Parser/serializer wrappers ===


def identity(x: Any) -> Any:
    return x


def traverse(
    col: Any,
    dict_callback: Callable[[Sequence[tuple[Any, Any]]], Any] = dict,
    list_callback: Callable[[Sequence[tuple[Any, Any]]], Any] = identity,
    key_callback: Callable[[Any], Any] = identity,
    instance_callbacks: Sequence[tuple[type, Any]] = (),
    default_callback: Callable[[Any], Any] = identity,
) -> Any:
    if isinstance(col, dict):
        res = dict_callback(
            [
                (
                    key_callback(k),
                    traverse(
                        v,
                        dict_callback,
                        list_callback,
                        key_callback,
                        instance_callbacks,
                        default_callback,
                    ),
                )
                for (k, v) in col.items()
            ]
        )
    elif isinstance(col, list):
        res = list_callback(
            [
                traverse(
                    x,
                    dict_callback,
                    list_callback,
                    key_callback,
                    instance_callbacks,
                    default_callback,
                )
                for x in col
            ]
        )
    else:
        for t, callback in instance_callbacks:
            if isinstance(col, t):
                res = callback(col)
                break
        else:
            res = default_callback(col)

    return res


Document = Union[bool, bytes, datetime.datetime, Mapping, None, Sequence, str]


def _decode_cbor(input_data: bytes) -> Document:
    try:
        doc = cbor2.loads(input_data)
        return cast(Document, doc)
    except cbor2.CBORDecodeError as e:
        msg = f"Cannot parse as CBOR ({e})"
        raise ValueError(msg)


def _decode_json(input_data: bytes) -> Document:
    try:
        doc = json.loads(
            input_data.decode(UTF_8),
        )

        return cast(Document, doc)
    except json.JSONDecodeError as e:
        msg = f"Cannot parse as JSON ({e})"
        raise ValueError(msg)


def _decode_msgpack(input_data: bytes) -> Document:
    try:
        doc = umsgpack.unpackb(input_data)
        return cast(Document, doc)
    except umsgpack.UnpackException as e:
        msg = f"Cannot parse as MessagePack ({e})"
        raise ValueError(msg)


def _decode_toml(input_data: bytes) -> Document:
    try:
        doc = tomllib.loads(input_data.decode(UTF_8))
        return cast(Document, doc)
    except tomllib.TOMLDecodeError as e:
        msg = f"Cannot parse as TOML ({e})"
        raise ValueError(msg)


def _decode_yaml(input_data: bytes) -> Document:
    try:
        yaml = ruamel.yaml.YAML(typ="safe")
        doc = yaml.load(input_data)

        return cast(Document, doc)
    except ruamel.yaml.YAMLError as e:
        problem = getattr(e, "problem", str(e))
        msg = f"Cannot parse as YAML ({problem})"
        raise ValueError(msg)


def decode(input_format: str, input_data: bytes) -> Document:
    decoder = {
        "cbor": _decode_cbor,
        "json": _decode_json,
        "msgpack": _decode_msgpack,
        "toml": _decode_toml,
        "yaml": _decode_yaml,
    }

    if input_format not in decoder:
        msg = f"Unknown input format: {input_format}"
        raise ValueError(msg)

    return decoder[input_format](input_data)


class TooManyValuesError(BaseException):
    pass


def _validate_value_count(doc: Document, *, maximum: int) -> None:
    if maximum < 0:
        return

    count = 0

    def count_callback(x: Any) -> Any:
        nonlocal count, maximum

        count += 1
        if count > maximum:
            msg = f"document contains too many values (over {maximum})"
            raise TooManyValuesError(msg)

        return x

    traverse(doc, instance_callbacks=[(object, count_callback)])


def _reject_special_keys(key: Any) -> Any:
    if isinstance(key, bool):
        msg = "boolean key"
        raise TypeError(msg)

    if isinstance(key, datetime.date):
        msg = "date key"
        raise TypeError(msg)

    if isinstance(key, datetime.datetime):
        msg = "date-time key"
        raise TypeError(msg)

    if isinstance(key, datetime.time):
        msg = "time key"
        raise TypeError(msg)

    if key is None:
        msg = "null key"
        raise TypeError(msg)

    return key


def _stringify_special_keys(key: Any) -> Any:
    if isinstance(key, bool):
        return "true" if key else "false"
    if isinstance(key, (datetime.date, datetime.datetime, datetime.time)):
        return key.isoformat()
    if key is None:
        return "null"

    return str(key)


def _encode_cbor(data: Document) -> bytes:
    try:
        return bytes(cbor2.dumps(data))
    except cbor2.CBOREncodeError as e:
        msg = f"Cannot convert data to CBOR ({e})"
        raise ValueError(msg)


def _json_default_stringify(obj: Any) -> str:
    if isinstance(obj, (datetime.date, datetime.datetime, datetime.time)):
        return obj.isoformat()
    msg = f"{obj!r} is not JSON serializable"
    raise TypeError(msg)


def _encode_json(
    data: Document,
    *,
    indent: int | None,
    sort_keys: bool,
    stringify: bool,
) -> str:
    separators = (",", ": " if indent else ":")

    if stringify:
        default_callback = _json_default_stringify
        key_callback = _stringify_special_keys
    else:
        default_callback = None
        key_callback = _reject_special_keys

    try:
        return (
            json.dumps(
                traverse(
                    data,
                    key_callback=key_callback,
                ),
                default=default_callback,
                ensure_ascii=False,
                indent=indent,
                separators=separators,
                sort_keys=sort_keys,
            )
            + "\n"
        )
    except (TypeError, ValueError) as e:
        msg = f"Cannot convert data to JSON ({e})"
        raise ValueError(msg)


def _msgpack_reject_local_datetime(obj: datetime.datetime) -> None:
    if obj.tzinfo is None:
        msg = "'datetime.datetime' without a time zone is unsupported"
        raise TypeError(msg)


def _encode_msgpack(data: Document) -> bytes:
    try:
        traverse(
            data,
            instance_callbacks=[(datetime.datetime, _msgpack_reject_local_datetime)],
        )

        return umsgpack.packb(data)
    except (TypeError, umsgpack.UnsupportedTypeException) as e:
        msg = f"Cannot convert data to MessagePack ({e})"
        raise ValueError(msg)


def _encode_python(
    data: Document,
    *,
    sort_keys: bool,
    width: int,
) -> bytes:
    return bytes(
        pprint.pformat(
            data,
            sort_dicts=sort_keys,
            width=width,
        )
        + "\n",
        UTF_8,
    )


def _encode_toml(
    data: Mapping[Any, Any],
    *,
    sort_keys: bool,
    stringify: bool,
) -> str:
    key_callback = _stringify_special_keys if stringify else _reject_special_keys

    def reject_null(x: Any) -> Any:
        if x is None:
            msg = "null values are not supported"
            raise TypeError(msg)

        return x

    def stringify_null(x: Any) -> Any:
        if x is None:
            return "null"

        return x

    default_callback = stringify_null if stringify else reject_null

    try:
        return tomlkit.dumps(
            traverse(
                data,
                key_callback=key_callback,
                default_callback=default_callback,
            ),
            sort_keys=sort_keys,
        )
    except AttributeError as e:
        if str(e) == "'list' object has no attribute 'as_string'":
            msg = (
                "Cannot convert non-dictionary data to TOML; "
                'use "--wrap" to wrap it in a dictionary'
            )
            raise ValueError(msg)
        else:
            raise e
    except (TypeError, ValueError) as e:
        msg = f"Cannot convert data to TOML ({e})"
        raise ValueError(msg)


def _yaml_represent_none(self, data):
    return self.represent_scalar("tag:yaml.org,2002:null", "null")


def _encode_yaml(
    data: Document,
    *,
    indent: int | None,
    options: FormatOptions | None,
    width: int,
) -> str:
    if options is None:
        options = YAMLOptions()

    if not isinstance(options, YAMLOptions):
        msg = "'options' not of type 'YAMLOptions'"
        raise TypeError(msg)

    yaml = ruamel.yaml.YAML()
    yaml.default_flow_style = False

    yaml.default_style = options.style  # type: ignore
    yaml.indent = indent
    yaml.width = width

    yaml.representer.add_representer(type(None), _yaml_represent_none)

    try:
        out = StringIO()
        yaml.dump(
            data,
            out,
        )

        return out.getvalue()
    except ruamel.yaml.YAMLError as e:
        problem = getattr(e, "problem", str(e))
        msg = f"Cannot convert data to YAML ({problem})"
        raise ValueError(msg)


def encode(
    output_format: str,
    data: Document,
    *,
    indent: int | None,
    options: FormatOptions | None,
    sort_keys: bool,
    stringify: bool,
    width: int,
) -> bytes:
    if output_format == "json":
        encoded = _encode_json(
            data,
            indent=indent,
            sort_keys=sort_keys,
            stringify=stringify,
        ).encode(UTF_8)
    elif output_format == "msgpack":
        encoded = _encode_msgpack(data)
    elif output_format == "python":
        encoded = _encode_python(data, sort_keys=sort_keys, width=width)
    elif output_format == "toml":
        if not isinstance(data, Mapping):
            msg = (
                f"Top-level value of type '{type(data).__name__}' cannot "
                "be encoded as TOML"
            )
            raise TypeError(msg)
        encoded = _encode_toml(data, sort_keys=sort_keys, stringify=stringify).encode(
            UTF_8
        )
    elif output_format == "yaml":
        encoded = _encode_yaml(
            data,
            indent=indent,
            options=options,
            width=width,
        ).encode(UTF_8)
    elif output_format == "msgpack":
        encoded = _encode_msgpack(data)
    elif output_format == "cbor":
        encoded = _encode_cbor(data)
    else:
        msg = f"Unknown output format: {output_format}"
        raise ValueError(msg)

    return encoded


# === Main ===


def remarshal(  # noqa: PLR0913
    input_format: str,
    output_format: str,
    input: Path | str,
    output: Path | str,
    *,
    indent: int | None = None,
    max_values: int = Defaults.MAX_VALUES,
    options: FormatOptions | None = None,
    sort_keys: bool = True,
    stringify: bool = False,
    transform: Callable[[Document], Document] | None = None,
    unwrap: str | None = None,
    width: int = CLIDefaults.WIDTH,
    wrap: str | None = None,
) -> None:
    input_file = None
    output_file = None

    try:
        input_file = sys.stdin.buffer if input == "-" else Path(input).open("rb")
        output_file = sys.stdout.buffer if output == "-" else Path(output).open("wb")

        input_data = input_file.read()
        if not isinstance(input_data, bytes):
            msg = "input_data must be bytes"
            raise TypeError(msg)

        parsed = decode(input_format, input_data)

        _validate_value_count(parsed, maximum=max_values)

        if unwrap is not None:
            if not isinstance(parsed, Mapping):
                msg = (
                    f"Top-level value of type '{type(parsed).__name__}' "
                    "cannot be unwrapped"
                )
                raise TypeError(msg)
            parsed = parsed[unwrap]
        if wrap is not None:
            temp = {}
            temp[wrap] = parsed
            parsed = temp

        if transform:
            parsed = transform(parsed)

        encoded = encode(
            output_format,
            parsed,
            indent=indent,
            options=options,
            sort_keys=sort_keys,
            stringify=stringify,
            width=width,
        )

        output_file.write(encoded)
    finally:
        if input_file is not None:
            input_file.close()
        if output != "-" and output_file is not None:
            output_file.close()


def main() -> None:
    args = _parse_command_line(sys.argv)

    try:
        remarshal(
            args.input_format,
            args.output_format,
            args.input,
            args.output,
            indent=args.indent,
            max_values=args.max_values,
            options=args.yaml_options,
            sort_keys=args.sort_keys,
            stringify=args.stringify,
            unwrap=args.unwrap,
            wrap=args.wrap,
        )
    except KeyboardInterrupt:
        pass
    except (OSError, TooManyValuesError, TypeError, ValueError) as e:
        msg = traceback.format_exc() if args.verbose else f"Error: {e}\n"
        print(msg, end="", file=sys.stderr)  # noqa: T201
        sys.exit(1)


if __name__ == "__main__":
    main()
