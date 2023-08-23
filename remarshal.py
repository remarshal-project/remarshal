#! /usr/bin/env python3
# Remarshal, a utility to convert between serialization formats.
# Copyright (c) 2014-2020, 2023 D. Bohdan
# License: MIT


from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Sequence, Set, Tuple, Union, cast

import cbor2  # type: ignore
import dateutil.parser
import tomlkit
import tomlkit.exceptions
import tomlkit.items
import umsgpack  # type: ignore
import yaml
import yaml.parser
import yaml.scanner

__version__ = "0.17.0"

FORMATS = ["cbor", "json", "msgpack", "toml", "yaml"]


# === YAML ===


# An ordered dumper for PyYAML.
class OrderedDumper(yaml.SafeDumper):
    pass


def mapping_representer(dumper: Any, data: Any) -> Any:
    return dumper.represent_mapping(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, data.items()
    )


OrderedDumper.add_representer(dict, mapping_representer)


# Fix loss of time zone information in PyYAML.
# http://stackoverflow.com/questions/13294186/can-pyyaml-parse-iso8601-dates
class TimezoneLoader(yaml.SafeLoader):
    pass


def timestamp_constructor(loader: Any, node: Any) -> datetime.datetime:
    return dateutil.parser.parse(node.value)


loaders = [TimezoneLoader]
for loader in loaders:
    loader.add_constructor("tag:yaml.org,2002:timestamp", timestamp_constructor)


# === CLI ===


def argv0_to_format(argv0: str) -> Tuple[str, str]:
    possible_format = "(" + "|".join(FORMATS) + ")"
    match = re.search("^" + possible_format + "2" + possible_format, argv0)
    from_, to = match.groups() if match else ("", "")
    return from_, to


def extension_to_format(path: str) -> str:
    ext = Path(path).suffix[1:]

    if ext == "yml":
        ext = "yaml"

    return ext if ext in FORMATS else ""


def parse_command_line(argv: List[str]) -> argparse.Namespace:  # noqa: C901.
    defaults: Dict[str, Any] = {
        "json_indent": None,
        "ordered": True,
        "stringify": False,
        "yaml_options": {},
    }

    me = Path(argv[0]).name
    argv0_from, argv0_to = argv0_to_format(me)
    format_from_argv0 = argv0_to != ""

    parser = argparse.ArgumentParser(
        description="Convert between CBOR, JSON, MessagePack, TOML, and YAML."
    )
    parser.add_argument("-v", "--version", action="version", version=__version__)

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("input", nargs="?", default="-", help="input file")
    input_group.add_argument(
        "-i",
        "--input",
        dest="input_flag",
        metavar="input",
        default=None,
        help="input file",
    )

    if not format_from_argv0:
        parser.add_argument(
            "--if",
            "-if",
            "--input-format",
            dest="input_format",
            default="",
            help="input format",
            choices=FORMATS,
        )

    if not format_from_argv0 or argv0_to == "json":
        parser.add_argument(
            "--json-indent",
            "--indent-json",
            dest="json_indent",
            metavar="n",
            type=int,
            default=defaults["json_indent"],
            help="JSON indentation",
        )

    if not format_from_argv0 or argv0_to in {"json", "toml"}:
        parser.add_argument(
            "-k",
            "--stringify",
            dest="stringify",
            action="store_true",
            help=(
                "Turn into strings boolean, date-time, and null keys for JSON "
                "and TOML and null values for TOML"
            ),
        )

    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("output", nargs="?", default="-", help="output file")
    output_group.add_argument(
        "-o",
        "--output",
        dest="output_flag",
        metavar="output",
        default=None,
        help="output file",
    )

    if not format_from_argv0:
        parser.add_argument(
            "--of",
            "-of",
            "--output-format",
            dest="output_format",
            default="",
            help="output format",
            choices=FORMATS,
        )

    parser.add_argument(
        "-p",
        "--preserve-key-order",
        help=argparse.SUPPRESS,
    )

    if not format_from_argv0 or argv0_to in {"json", "toml", "yaml"}:
        parser.add_argument(
            "-s",
            "--sort-keys",
            dest="ordered",
            action="store_false",
            help="sort JSON, TOML, YAML keys instead of preserving key order",
        )

    parser.add_argument(
        "--unwrap",
        dest="unwrap",
        metavar="key",
        default=None,
        help="only output the data stored under the given key",
    )
    parser.add_argument(
        "--wrap",
        dest="wrap",
        metavar="key",
        default=None,
        help="wrap the data in a map type with the given key",
    )

    if not format_from_argv0 or argv0_to == "yaml":
        parser.add_argument(
            "--yaml-indent",
            dest="yaml_indent",
            metavar="n",
            type=int,
            default=2,
            help="YAML indentation",
        )
        parser.add_argument(
            "--yaml-style",
            dest="yaml_style",
            default=None,
            help="YAML formatting style",
            choices=["", "'", '"', "|", ">"],
        )

        def yaml_width(value: str) -> int:
            # This is theoretically compatible with LibYAML.
            return (1 << 32) - 1 if value.lower() == "inf" else int(value)

        parser.add_argument(
            "--yaml-width",
            dest="yaml_width",
            metavar="n",
            type=yaml_width,  # Allow "inf".
            default=80,
            help="YAML line width for long strings",
        )

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
            args.input_format = extension_to_format(args.input)
            if args.input_format == "":
                parser.error("Need an explicit input format")

        if args.output_format == "":
            args.output_format = extension_to_format(args.output)
            if args.output_format == "":
                parser.error("Need an explicit output format")

    for key, value in defaults.items():
        vars(args).setdefault(key, value)

    # Wrap the yaml_* option.
    if "yaml_indent" in vars(args):
        vars(args)["yaml_options"] = {
            "default_style": args.yaml_style,
            "indent": args.yaml_indent,
            "width": args.yaml_width,
        }
        for key in ["yaml_indent", "yaml_style", "yaml_width"]:
            del vars(args)[key]

    return args


# === Parser/serializer wrappers ===


def identity(x: Any) -> Any:
    return x


def traverse(
    col: Any,
    dict_callback: Callable[[List[Tuple[Any, Any]]], Any] = lambda x: dict(x),
    list_callback: Callable[[List[Tuple[Any, Any]]], Any] = identity,
    key_callback: Callable[[Any], Any] = identity,
    instance_callbacks: Set[Tuple[type, Any]] = set(),
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


def decode_json(input_data: bytes) -> Document:
    try:
        doc = json.loads(
            input_data.decode("utf-8"),
        )

        return cast(Document, doc)
    except json.JSONDecodeError as e:
        msg = f"Cannot parse as JSON ({e})"
        raise ValueError(msg)


def decode_msgpack(input_data: bytes) -> Document:
    try:
        doc = umsgpack.unpackb(input_data)
        return cast(Document, doc)
    except umsgpack.UnpackException as e:
        msg = f"Cannot parse as MessagePack ({e})"
        raise ValueError(msg)


def decode_cbor(input_data: bytes) -> Document:
    try:
        doc = cbor2.loads(input_data)
        return cast(Document, doc)
    except cbor2.CBORDecodeError as e:
        msg = f"Cannot parse as CBOR ({e})"
        raise ValueError(msg)


def decode_toml(input_data: bytes) -> Document:
    try:
        # Remove TOML Kit's custom classes.
        # https://github.com/sdispater/tomlkit/issues/43
        doc = traverse(
            tomlkit.loads(input_data),
            instance_callbacks={
                (tomlkit.items.Bool, bool),
                (
                    tomlkit.items.Date,
                    lambda x: datetime.date(
                        x.year,
                        x.month,
                        x.day,
                    ),
                ),
                (
                    tomlkit.items.DateTime,
                    lambda x: datetime.datetime(
                        x.year,
                        x.month,
                        x.day,
                        x.hour,
                        x.minute,
                        x.second,
                        x.microsecond,
                        x.tzinfo,
                    ),
                ),
                (tomlkit.items.Float, float),
                (tomlkit.items.Integer, int),
                (tomlkit.items.String, str),
                (
                    tomlkit.items.Time,
                    lambda x: datetime.time(
                        x.hour,
                        x.minute,
                        x.second,
                        x.microsecond,
                        x.tzinfo,
                    ),
                ),
            },
        )

        return cast(Document, doc)
    except tomlkit.exceptions.ParseError as e:
        msg = f"Cannot parse as TOML ({e})"
        raise ValueError(msg)


def decode_yaml(input_data: bytes) -> Document:
    try:
        loader = TimezoneLoader
        doc = yaml.load(input_data, loader)
        return cast(Document, doc)
    except (yaml.scanner.ScannerError, yaml.parser.ParserError) as e:
        msg = f"Cannot parse as YAML ({e})"
        raise ValueError(msg)


def decode(input_format: str, input_data: bytes) -> Document:
    decoder = {
        "cbor": decode_cbor,
        "json": decode_json,
        "msgpack": decode_msgpack,
        "toml": decode_toml,
        "yaml": decode_yaml,
    }

    if input_format not in decoder:
        msg = f"Unknown input format: {input_format}"
        raise ValueError(msg)

    return decoder[input_format](input_data)


def reject_special_keys(key: Any) -> Any:
    if isinstance(key, bool):
        msg = "boolean key"
        raise TypeError(msg)
    if isinstance(key, datetime.datetime):
        msg = "date-time key"
        raise TypeError(msg)
    if key is None:
        msg = "null key"
        raise TypeError(msg)

    return key


def stringify_special_keys(key: Any) -> Any:
    if isinstance(key, bool):
        return "true" if key else "false"
    if isinstance(key, datetime.datetime):
        return key.isoformat()
    if key is None:
        return "null"

    return str(key)


def json_default(obj: Any) -> str:
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    msg = f"{obj!r} is not JSON-serializable"
    raise TypeError(msg)


def encode_json(
    data: Document,
    *,
    ordered: bool,
    indent: Union[bool, int, None],
    stringify: bool,
) -> str:
    if indent is True:
        indent = 2

    separators = (",", ": " if indent else ":")
    key_callback = stringify_special_keys if stringify else reject_special_keys

    try:
        return (
            json.dumps(
                traverse(
                    data,
                    key_callback=key_callback,
                ),
                default=json_default,
                ensure_ascii=False,
                indent=indent,
                separators=separators,
                sort_keys=not ordered,
            )
            + "\n"
        )
    except (TypeError, ValueError) as e:
        msg = f"Cannot convert data to JSON ({e})"
        raise ValueError(msg)


def encode_msgpack(data: Document) -> bytes:
    try:
        return bytes(umsgpack.packb(data))
    except umsgpack.UnsupportedTypeException as e:
        msg = f"Cannot convert data to MessagePack ({e})"
        raise ValueError(msg)


def encode_cbor(data: Document) -> bytes:
    try:
        return bytes(cbor2.dumps(data))
    except cbor2.CBOREncodeError as e:
        msg = f"Cannot convert data to CBOR ({e})"
        raise ValueError(msg)


def encode_toml(
    data: Mapping[Any, Any],
    *,
    ordered: bool,
    stringify: bool,
) -> str:
    key_callback = stringify_special_keys if stringify else reject_special_keys

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
            sort_keys=not ordered,
        )
    except AttributeError as e:
        if str(e) == "'list' object has no attribute 'as_string'":
            msg = (
                "Cannot convert non-dictionary data to TOML; "
                'use "wrap" to wrap it in a dictionary'
            )
            raise ValueError(msg)
        else:
            raise e
    except (TypeError, ValueError) as e:
        msg = f"Cannot convert data to TOML ({e})"
        raise ValueError(msg)


def encode_yaml(data: Document, *, ordered: bool, yaml_options: Dict[Any, Any]) -> str:
    dumper = OrderedDumper if ordered else yaml.SafeDumper
    try:
        return yaml.dump(
            data,
            None,
            dumper,
            allow_unicode=True,
            default_flow_style=False,
            encoding=None,
            **yaml_options,
        )
    except yaml.representer.RepresenterError as e:
        msg = f"Cannot convert data to YAML ({e})"
        raise ValueError(msg)


def encode(
    output_format: str,
    data: Document,
    *,
    json_indent: Union[int, None],
    ordered: bool,
    stringify: bool,
    yaml_options: Dict[Any, Any],
) -> bytes:
    if output_format == "json":
        encoded = encode_json(
            data,
            indent=json_indent,
            ordered=ordered,
            stringify=stringify,
        ).encode("utf-8")
    elif output_format == "msgpack":
        encoded = encode_msgpack(data)
    elif output_format == "toml":
        if not isinstance(data, Mapping):
            msg = (
                f"Top-level value of type '{type(data).__name__}' cannot "
                "be encoded as TOML"
            )
            raise TypeError(msg)
        encoded = encode_toml(data, ordered=ordered, stringify=stringify).encode(
            "utf-8"
        )
    elif output_format == "yaml":
        encoded = encode_yaml(data, ordered=ordered, yaml_options=yaml_options).encode(
            "utf-8"
        )
    elif output_format == "cbor":
        encoded = encode_cbor(data)
    else:
        msg = f"Unknown output format: {output_format}"
        raise ValueError(msg)

    return encoded


# === Main ===


def run(argv: List[str]) -> None:
    args = parse_command_line(argv)
    remarshal(
        args.input,
        args.output,
        args.input_format,
        args.output_format,
        json_indent=args.json_indent,
        ordered=args.ordered,
        stringify=args.stringify,
        unwrap=args.unwrap,
        wrap=args.wrap,
        yaml_options=args.yaml_options,
    )


def remarshal(
    input: Path | str,
    output: Path | str,
    input_format: str,
    output_format: str,
    *,
    json_indent: Union[int, None] = None,
    ordered: bool = True,
    stringify: bool = False,
    transform: Union[Callable[[Document], Document], None] = None,
    unwrap: Union[str, None] = None,
    wrap: Union[str, None] = None,
    yaml_options: Dict[Any, Any] = {},
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
            json_indent=json_indent,
            ordered=ordered,
            stringify=stringify,
            yaml_options=yaml_options,
        )

        output_file.write(encoded)
    finally:
        if input_file is not None:
            input_file.close()
        if output != "-" and output_file is not None:
            output_file.close()


def main() -> None:
    try:
        run(sys.argv)
    except KeyboardInterrupt:
        pass
    except (OSError, TypeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)  # noqa: T201
        sys.exit(1)


if __name__ == "__main__":
    main()
