#! /usr/bin/env python3
# Remarshal, a utility to convert between serialization formats.
# Copyright (c) 2014-2020, 2023 D. Bohdan
# License: MIT


import argparse
import datetime
import json
import os.path
import re
import sys

import cbor2  # type: ignore
import dateutil.parser
import tomlkit
import umsgpack  # type: ignore
import yaml

__version__ = "0.15.1"

FORMATS = ["cbor", "json", "msgpack", "toml", "yaml"]


# === YAML ===


# An ordered dumper for PyYAML.
class OrderedDumper(yaml.SafeDumper):
    pass


def mapping_representer(dumper, data):
    return dumper.represent_mapping(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, data.items()
    )


OrderedDumper.add_representer(dict, mapping_representer)


# Fix loss of time zone information in PyYAML.
# http://stackoverflow.com/questions/13294186/can-pyyaml-parse-iso8601-dates
class TimezoneLoader(yaml.SafeLoader):
    pass


def timestamp_constructor(loader, node):
    return dateutil.parser.parse(node.value)


loaders = [TimezoneLoader]
for loader in loaders:
    loader.add_constructor("tag:yaml.org,2002:timestamp", timestamp_constructor)


# === JSON ===


def json_default(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    msg = f"{obj!r} is not JSON serializable"
    raise TypeError(msg)


# === CLI ===


def argv0_to_format(argv0):
    possible_format = "(" + "|".join(FORMATS) + ")"
    match = re.search("^" + possible_format + "2" + possible_format, argv0)
    from_, to = match.groups() if match else (None, None)
    return bool(match), from_, to


def extension_to_format(path):
    _, ext = os.path.splitext(path)

    ext = ext[1:]

    if ext == "yml":
        ext = "yaml"

    return ext if ext in FORMATS else None


def parse_command_line(argv):
    me = os.path.basename(argv[0])
    format_from_argv0, argv0_from, argv0_to = argv0_to_format(me)

    parser = argparse.ArgumentParser(
        description="Convert between CBOR, JSON, MessagePack, TOML, and YAML."
    )

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
            "--if",
            "-if",
            "--input-format",
            dest="input_format",
            help="input format",
            choices=FORMATS,
        )
        parser.add_argument(
            "--of",
            "-of",
            "--output-format",
            dest="output_format",
            help="output format",
            choices=FORMATS,
        )

    if not format_from_argv0 or argv0_to == "json":
        parser.add_argument(
            "--indent-json",
            dest="indent_json",
            metavar="n",
            type=int,
            default=None,
            help="indent JSON output",
        )

    if not format_from_argv0 or argv0_to == "yaml":
        parser.add_argument(
            "--yaml-style",
            dest="yaml_style",
            default=None,
            help="YAML formatting style",
            choices=["", "'", '"', "|", ">"],
        )

    parser.add_argument(
        "--wrap",
        dest="wrap",
        metavar="key",
        default=None,
        help="wrap the data in a map type with the given key",
    )
    parser.add_argument(
        "--unwrap",
        dest="unwrap",
        metavar="key",
        default=None,
        help="only output the data stored under the given key",
    )
    parser.add_argument(
        "-p",
        "--preserve-key-order",
        dest="ordered",
        action="store_true",
        help="preserve the order of dictionary/mapping keys when encoding",
    )
    parser.add_argument("-v", "--version", action="version", version=__version__)

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

        if argv0_to != "json":
            args.__dict__["indent_json"] = None
        if argv0_to != "yaml":
            args.__dict__["yaml_style"] = None
    else:
        if args.input_format is None:
            args.input_format = extension_to_format(args.input)
            if args.input_format is None:
                parser.error("Need an explicit input format")

        if args.output_format is None:
            args.output_format = extension_to_format(args.output)
            if args.output_format is None:
                parser.error("Need an explicit output format")

    # Wrap yaml_style.
    args.__dict__["yaml_options"] = {"default_style": args.yaml_style}
    del args.__dict__["yaml_style"]

    return args


# === Parser/serializer wrappers ===


def traverse(
    col,
    dict_callback=lambda x: dict(x),
    list_callback=lambda x: x,
    key_callback=lambda x: x,
    instance_callbacks=[],
    default_callback=lambda x: x,
):
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


def decode_json(input_data):
    try:
        return json.loads(
            input_data.decode("utf-8"),
        )
    except json.JSONDecodeError as e:
        msg = f"Cannot parse as JSON ({e})"
        raise ValueError(msg)


def decode_msgpack(input_data):
    try:
        return umsgpack.unpackb(input_data)
    except umsgpack.UnpackException as e:
        msg = f"Cannot parse as MessagePack ({e})"
        raise ValueError(msg)


def decode_cbor(input_data):
    try:
        return cbor2.loads(input_data)
    except cbor2.CBORDecodeError as e:
        msg = f"Cannot parse as CBOR ({e})"
        raise ValueError(msg)


def decode_toml(input_data):
    try:
        # Remove TOML Kit's custom classes.
        # https://github.com/sdispater/tomlkit/issues/43
        return traverse(
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
    except tomlkit.exceptions.ParseError as e:
        msg = f"Cannot parse as TOML ({e})"
        raise ValueError(msg)


def decode_yaml(input_data):
    try:
        loader = TimezoneLoader
        return yaml.load(input_data, loader)
    except (yaml.scanner.ScannerError, yaml.parser.ParserError) as e:
        msg = f"Cannot parse as YAML ({e})"
        raise ValueError(msg)


def decode(input_format, input_data):
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


def encode_json(data, ordered, indent):
    if indent is True:
        indent = 2

    separators = (",", ": " if indent else ":")

    def stringify_key(key):
        if isinstance(key, bool):
            return "true" if key else "false"
        return "null" if key is None else key

    try:
        return (
            json.dumps(
                traverse(
                    data,
                    key_callback=stringify_key,
                ),
                default=json_default,
                ensure_ascii=False,
                indent=indent,
                separators=separators,
                sort_keys=not ordered,
            )
            + "\n"
        )
    except TypeError as e:
        msg = f"Cannot convert data to JSON ({e})"
        raise ValueError(msg)


def encode_msgpack(data):
    try:
        return umsgpack.packb(data)
    except umsgpack.UnsupportedTypeException as e:
        msg = f"Cannot convert data to MessagePack ({e})"
        raise ValueError(msg)


def encode_cbor(data):
    try:
        return cbor2.dumps(data)
    except cbor2.CBOREncodeError as e:
        msg = f"Cannot convert data to CBOR ({e})"
        raise ValueError(msg)


def encode_toml(data, ordered):
    try:
        return tomlkit.dumps(data, sort_keys=not ordered)
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


def encode_yaml(data, ordered, yaml_options):
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


# === Main ===


def run(argv):
    args = parse_command_line(argv)
    remarshal(
        args.input,
        args.output,
        args.input_format,
        args.output_format,
        args.wrap,
        args.unwrap,
        args.indent_json,
        args.yaml_options,
        args.ordered,
    )


def remarshal(
    input,
    output,
    input_format,
    output_format,
    wrap=None,
    unwrap=None,
    indent_json=None,
    yaml_options={},
    ordered=False,
    transform=None,
):
    try:
        if input == "-":
            input_file = getattr(sys.stdin, "buffer", sys.stdin)
        else:
            input_file = open(input, "rb")

        if output == "-":
            output_file = getattr(sys.stdout, "buffer", sys.stdout)
        else:
            output_file = open(output, "wb")

        input_data = input_file.read()

        parsed = decode(input_format, input_data)

        if unwrap is not None:
            parsed = parsed[unwrap]
        if wrap is not None:
            temp = {}
            temp[wrap] = parsed
            parsed = temp

        if transform:
            parsed = transform(parsed)

        if output_format == "json":
            output_data = encode_json(parsed, ordered, indent_json)
        elif output_format == "msgpack":
            output_data = encode_msgpack(parsed)
        elif output_format == "toml":
            output_data = encode_toml(parsed, ordered)
        elif output_format == "yaml":
            output_data = encode_yaml(parsed, ordered, yaml_options)
        elif output_format == "cbor":
            output_data = encode_cbor(parsed)
        else:
            msg = f"Unknown output format: {output_format}"
            raise ValueError(msg)

        if output_format == "msgpack" or output_format == "cbor":
            encoded = output_data
        else:
            encoded = output_data.encode("utf-8")
        output_file.write(encoded)

        output_file.close()
    finally:
        if "input_file" in locals():
            input_file.close()
        if "output_file" in locals():
            output_file.close()


def main():
    try:
        run(sys.argv)
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)  # noqa: T201
        sys.exit(1)


if __name__ == "__main__":
    main()
