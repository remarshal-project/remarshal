#! /usr/bin/env python3
# Remarshal, a utility to convert between serialization formats.
# Copyright (c) 2014-2020, 2024-2026 D. Bohdan
# License: MIT

from __future__ import annotations

import argparse
import importlib.metadata
import re
import sys
import traceback
from pathlib import Path
from typing import (
    Callable,
    Iterable,
    Mapping,
    Sequence,
)

import colorama
from termcolor import colored

# Importing the codecs package registers every built-in `Encoder` and `Decoder`.
from remarshal import codecs as _codecs  # noqa: F401
from remarshal.codec import (
    DECODERS,
    ENCODERS,
    Decoder,
    Encoder,
    decode,
    encode,
    get_decoder,
    get_encoder,
)
from remarshal.document import (
    Document,
    TooManyValuesError,
    contains_tagged_value,
    envelopes_to_tags,
    identity,
    tags_to_envelopes,
    traverse,
    validate_value_count,
)
from remarshal.options import (
    CBOROptions,
    Defaults,
    FormatOptions,
    JSONOptions,
    MsgPackOptions,
    PythonOptions,
    TOMLOptions,
    YAMLOptions,
    YAMLStyle,
    YAMLVersion,
)
from remarshal.starlark_transform import compile_transform

__all__ = [
    # Constants.
    "INPUT_FORMATS",
    "OUTPUT_FORMATS",
    # Classes and static types.
    "Decoder",
    "Defaults",
    "Document",
    "Encoder",
    "TooManyValuesError",
    "YAMLStyle",
    "YAMLVersion",
    # Format dataclasses.
    "FormatOptions",
    "CBOROptions",
    "JSONOptions",
    "MsgPackOptions",
    "PythonOptions",
    "TOMLOptions",
    "YAMLOptions",
    # Codec registries.
    "DECODERS",
    "ENCODERS",
    "get_decoder",
    "get_encoder",
    # Functions.
    "decode",
    "encode",
    "format_options",
    "identity",
    "main",
    "remarshal",
    "traverse",
]


INPUT_FORMATS = ["cbor", "json", "msgpack", "toml", "yaml", "yaml-1.1", "yaml-1.2"]
OUTPUT_FORMATS = [
    "cbor",
    "json",
    "msgpack",
    "python",
    "toml",
    "yaml",
    "yaml-1.1",
    "yaml-1.2",
]
OUTPUT_FORMATS_ARGV0 = [
    "cbor",
    "json",
    "msgpack",
    "py",
    "toml",
    "yaml",
    "yaml-1.1",
    "yaml-1.2",
]

# === CLI ===


class ColorHelpFormatter(argparse.HelpFormatter):
    """An `argparse` help formatter
    that prints option strings and metavars in color (green).

    Color is applied on top of the plain layout produced by the base formatter.
    This means column alignment and usage line wrapping stay correct.
    The termcolor library handles cross-platform support
    and disables color when the output is not a terminal or `NO_COLOR` is set.
    """

    @staticmethod
    def _optional_color(text: str, *, color: bool = True) -> str:
        return colored(text, "green") if color else text

    def _format_action_invocation(
        self, action: argparse.Action, *, color: bool = False
    ) -> str:
        # Reproduce the condensed Python 3.13+ style ("-s, --long ARGS")
        # on every supported version so the output does not change across them.
        c = self._optional_color

        if not action.option_strings:
            (metavar,) = self._metavar_formatter(
                action, self._get_default_metavar_for_positional(action)
            )(1)

            return c(metavar, color=color)

        opts = ", ".join(c(option, color=color) for option in action.option_strings)

        if action.nargs == 0:
            return opts

        default = self._get_default_metavar_for_optional(action)
        args_string = self._format_args(action, default)

        return opts + " " + c(args_string, color=color)

    def _format_action(self, action: argparse.Action) -> str:
        text = super()._format_action(action)

        # Swap the plain invocation for a colored one of the same visible width
        # so the help-text column stays aligned.
        invocation = self._format_action_invocation(action)

        if invocation:
            colored_invocation = self._format_action_invocation(action, color=True)
            text = text.replace(invocation, colored_invocation, 1)

        return text

    def _format_usage(
        self,
        usage: str | None,
        actions: Iterable[argparse.Action],
        groups: Iterable[argparse._MutuallyExclusiveGroup],
        prefix: str | None,
    ) -> str:
        text = super()._format_usage(usage, actions, groups, prefix)

        # Color metavars (`<n>`, `{a,b}`)
        # and then option strings (`-o`, `--option`).
        # The lookarounds keep the option pattern
        # from matching choice values such as `yaml-1.1`
        # inside an already-colored metavar.
        text = re.sub(r"<[^>]+>|\{[^}]*\}", lambda m: self._optional_color(m[0]), text)
        text = re.sub(
            r"(?<![\w-])--?[A-Za-z][\w-]*",
            lambda m: self._optional_color(m[0]),
            text,
        )

        for action in actions:
            if action.option_strings:
                continue

            (metavar,) = self._metavar_formatter(
                action, self._get_default_metavar_for_positional(action)
            )(1)

            # The `<` and `>` boundaries stop a bare positional metavar like `input`
            # from matching again inside an already-colored `<input>`.
            text = re.sub(
                rf"(?<![\w<-]){re.escape(metavar)}(?![\w>-])",
                lambda m: self._optional_color(m[0]),
                text,
            )

        return text


def _argv0_to_format(argv0: str) -> tuple[str, str]:
    possible_input_format = "(" + "|".join(INPUT_FORMATS) + ")"
    possible_output_format = "(" + "|".join(OUTPUT_FORMATS_ARGV0) + ")"

    match = re.search("^" + possible_input_format + "2" + possible_output_format, argv0)
    from_, to = match.groups() if match else ("", "")

    if to == "py":
        to = "python"

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

    parser = argparse.ArgumentParser(
        description="Convert between CBOR, JSON, MessagePack, TOML, and YAML.",
        formatter_class=ColorHelpFormatter,
        prog="remarshal",
    )

    if sys.version_info >= (3, 14):
        parser.color = False

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=importlib.metadata.version("remarshal"),
    )

    if not format_from_argv0:
        parser.add_argument(
            "-f",
            "--from",
            "--if",
            "--input-format",
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

    parser.add_argument(
        "--indent",
        default=Defaults.INDENT,
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

    parser.add_argument(
        "--multiline",
        default=Defaults.MULTILINE_THRESHOLD,
        dest="multiline_threshold",
        metavar="<n>",
        type=int,
        help=(
            "minimum number of items to make non-nested TOML array multiline "
            "(default %(default)s)"
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

    starlark_group = parser.add_mutually_exclusive_group()
    starlark_group.add_argument(
        "--starlark",
        default=None,
        metavar="<code>",
        help=(
            "transform the data with a Starlark expression or program; "
            "the input is bound to 'data'; the program must assign the "
            "output to 'result'"
        ),
    )
    starlark_group.add_argument(
        "--starlark-file",
        default=None,
        metavar="<path>",
        help="read a Starlark program from a file",
    )

    allocs_megs = 128
    meg = 1024 * 1024

    parser.add_argument(
        "--starlark-max-allocs",
        default=allocs_megs * meg,
        metavar="<n>",
        type=int,
        help=(
            "maximum cumulative bytes of Starlark allocations "
            f"(default {allocs_megs} * {meg}, negative for unlimited)"
        ),
    )

    parser.add_argument(
        "--starlark-max-steps",
        default=10_000_000,
        metavar="<n>",
        type=int,
        help=(
            "maximum number of Starlark interpreter steps "
            "(default %(default)s, negative for unlimited)"
        ),
    )

    if not format_from_argv0:
        parser.add_argument(
            "-t",
            "--to",
            "--of",
            "--output-format",
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
        default=Defaults.WIDTH,
        metavar="<n>",
        type=output_width,  # Allow "inf".
        help=(
            "Python line width and YAML line width for long strings (integer or 'inf')"
        ),
    )

    parser.add_argument(
        "--wrap",
        default=None,
        metavar="<key>",
        help="wrap the data in a map type with the given key",
    )

    parser.add_argument(
        "--yaml-expand-aliases",
        dest="expand_aliases",
        action="store_true",
        help="expand YAML aliases (disable anchor/alias generation)",
    )

    # Hidden alias kept for backward compatibility.
    parser.add_argument(
        "--expand-aliases",
        dest="expand_aliases",
        action="store_true",
        help=argparse.SUPPRESS,
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
        "--yaml-style-newline",
        choices=["", "'", '"', "|", ">"],
        default=YAMLOptions().style_newline,
        help="YAML formatting style override for strings that contain a newline",
    )

    parser.add_argument(
        "--yaml-tags",
        action="store_true",
        help=(
            "translate between YAML tags and single-key mappings with the tag as key "
            "(for example, '!secret foo' and {'!secret': 'foo'}) "
            "so tags survive conversion to and from other formats"
        ),
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

    return args


# === Public API ===


def format_options(
    output_format: str,
    *,
    expand_aliases: bool = False,
    indent: int | None = None,
    multiline_threshold: int = Defaults.MULTILINE_THRESHOLD,
    sort_keys: bool = False,
    stringify: bool = False,
    width: int = Defaults.WIDTH,
    yaml_style: YAMLStyle = Defaults.YAML_STYLE,
    yaml_style_newline: YAMLStyle | None = None,
) -> FormatOptions:
    match output_format:
        case "cbor":
            return CBOROptions()

        case "json":
            return JSONOptions(
                indent=indent,
                sort_keys=sort_keys,
                stringify=stringify,
            )

        case "msgpack":
            return MsgPackOptions()

        case "python":
            return PythonOptions(
                indent=indent,
                sort_keys=sort_keys,
                width=width,
            )

        case "toml":
            return TOMLOptions(
                multiline_threshold=multiline_threshold,
                sort_keys=sort_keys,
                stringify=stringify,
            )

        case "yaml" | "yaml-1.1" | "yaml-1.2":
            yaml_version: YAMLVersion = None
            if output_format == "yaml-1.1":
                yaml_version = (1, 1)
            elif output_format == "yaml-1.2":
                yaml_version = (1, 2)
            return YAMLOptions(
                expand_aliases=expand_aliases,
                indent=Defaults.YAML_INDENT if indent is None else indent,
                style=yaml_style,
                style_newline=yaml_style_newline,
                version=yaml_version,
                width=width,
            )

        case _:
            msg = f"Unknown output format: {output_format}"
            raise ValueError(msg)


# === Main ===


def remarshal(
    input_format: str,
    output_format: str,
    input: Path | str,
    output: Path | str,
    *,
    max_values: int = Defaults.MAX_VALUES,
    options: FormatOptions | None = None,
    transform: Callable[[Document], Document] | None = None,
    unwrap: str | None = None,
    wrap: str | None = None,
    yaml_tags: bool = False,
) -> None:
    input_file = None
    output_file = None

    if options is None:
        options = format_options(output_format)

    try:
        input_file = sys.stdin.buffer if input == "-" else Path(input).open("rb")
        output_file = sys.stdout.buffer if output == "-" else Path(output).open("wb")

        input_data = input_file.read()
        if not isinstance(input_data, bytes):
            msg = "'input_data' must be 'bytes'"
            raise TypeError(msg)

        parsed = decode(input_format, input_data)

        validate_value_count(parsed, maximum=max_values)

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
            # Re-check after a user transform: it may have produced more
            # values than the input did.
            validate_value_count(parsed, maximum=max_values)

        yaml_output = output_format in ("yaml", "yaml-1.1", "yaml-1.2")
        if yaml_tags:
            # Move between native YAML tags and their mapping envelopes.
            parsed = (
                envelopes_to_tags(parsed) if yaml_output else tags_to_envelopes(parsed)
            )
        elif not yaml_output and contains_tagged_value(parsed):
            msg = (
                "input contains a YAML tag, which the output format cannot "
                "represent; use '--yaml-tags' to convert tags to mappings"
            )
            raise ValueError(msg)

        encoded = encode(
            output_format,
            parsed,
            options=options,
        )

        output_file.write(encoded)
    finally:
        if input_file is not None:
            input_file.close()
        if output != "-" and output_file is not None:
            output_file.close()


def _build_starlark_transform(
    args: argparse.Namespace,
) -> Callable[[Document], Document] | None:
    if args.starlark is None and args.starlark_file is None:
        return None

    if args.starlark_file is not None:
        source = Path(args.starlark_file).read_text(encoding="utf-8")
        filename = args.starlark_file
    else:
        source = args.starlark
        filename = "<starlark>"

    def to_limit(n: int) -> int | None:
        return None if n < 0 else n

    return compile_transform(
        source,
        filename=filename,
        max_steps=to_limit(args.starlark_max_steps),
        max_allocs=to_limit(args.starlark_max_allocs),
    )


def main() -> None:
    args = _parse_command_line(sys.argv)

    try:
        options = format_options(
            args.output_format,
            expand_aliases=args.expand_aliases,
            indent=args.indent,
            multiline_threshold=args.multiline_threshold,
            sort_keys=args.sort_keys,
            stringify=args.stringify,
            width=args.width,
            yaml_style=args.yaml_style,
            yaml_style_newline=args.yaml_style_newline,
        )

        transform = _build_starlark_transform(args)

        remarshal(
            args.input_format,
            args.output_format,
            args.input,
            args.output,
            max_values=args.max_values,
            options=options,
            transform=transform,
            unwrap=args.unwrap,
            wrap=args.wrap,
            yaml_tags=args.yaml_tags,
        )
    except KeyboardInterrupt:
        pass
    except (OSError, TooManyValuesError, TypeError, ValueError) as e:
        msg = traceback.format_exc() if args.verbose else f"Error: {e}\n"
        print(msg, end="", file=sys.stderr)  # noqa: T201
        sys.exit(1)


if __name__ == "__main__":
    main()
