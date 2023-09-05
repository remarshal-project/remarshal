#! /usr/bin/env python
# Remarshal, a utility to convert between serialization formats.
# Copyright (c) 2014-2020, 2023 D. Bohdan
# License: MIT

from __future__ import annotations

import datetime
import errno
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple, Union

import cbor2  # type: ignore
import pytest

from .context import remarshal

TEST_PATH = Path(__file__).resolve().parent


def data_file_path(filename: str) -> str:
    path_list = []
    if re.match(r"example\.(json|msgpack|toml|yaml|cbor)$", filename):
        path_list.append("..")
    path_list.append(filename)
    return str(TEST_PATH.joinpath(*path_list))


def read_file(filename: str) -> bytes:
    with Path(data_file_path(filename)).open("rb") as f:
        return f.read()


def sorted_dict(pairs: List[Tuple[Any, Any]]) -> Dict[Any, Any]:
    return dict(sorted(pairs))


def toml_signature(data: bytes | str) -> List[str]:
    """Return a lossy representation of TOML example data for comparison."""

    def strip_more(line: str) -> str:
        return re.sub(r" *#.*$", "", line.strip()).replace(" ", "")

    def sig_lines(lst: List[str]) -> List[str]:
        def should_drop(line: str) -> bool:
            return (
                line.startswith("#")
                or line in ("", "]")
                or bool(re.match(r'^".*",?$', line))
                or bool(re.match(r"^hosts", line))
            )

        return sorted(
            [strip_more(line) for line in lst if not should_drop(strip_more(line))]
        )

    str_data = data if isinstance(data, str) else data.decode("utf-8")

    return sig_lines(str_data.split("\n"))


class TestRemarshal(unittest.TestCase):
    def temp_filename(self) -> str:
        fd, temp_filename = tempfile.mkstemp()
        os.close(fd)
        self.temp_files.append(temp_filename)
        return temp_filename

    def assert_cbor_same(self, output: bytes, reference: bytes) -> None:
        # To date, Python's CBOR libraries don't support encoding to
        # canonical-form CBOR, so we have to parse and deep-compare.
        output_dec = cbor2.loads(output)
        reference_dec = cbor2.loads(reference)
        assert output_dec == reference_dec

    def convert_and_read(
        self,
        input: str,
        input_format: str,
        output_format: str,
        *,
        json_indent: Union[int, None] = 2,
        ordered: bool = False,
        stringify: bool = False,
        transform: Union[
            Callable[[remarshal.Document], remarshal.Document], None
        ] = None,
        unwrap: Union[str, None] = None,
        wrap: Union[str, None] = None,
        yaml_options: Dict[Any, Any] = {},
    ) -> bytes:
        output_filename = self.temp_filename()
        remarshal.remarshal(
            data_file_path(input),
            output_filename,
            input_format,
            output_format,
            json_indent=json_indent,
            ordered=ordered,
            stringify=stringify,
            transform=transform,
            unwrap=unwrap,
            wrap=wrap,
            yaml_options=yaml_options,
        )

        return read_file(output_filename)

    def setUp(self) -> None:
        self.maxDiff = None
        self.temp_files: List[str] = []

    def tearDown(self) -> None:
        for filename in self.temp_files:
            Path(filename).unlink()

    def test_json2json(self) -> None:
        output = self.convert_and_read("example.json", "json", "json")
        reference = read_file("example.json")
        assert output == reference

    def test_msgpack2msgpack(self) -> None:
        output = self.convert_and_read(
            "example.msgpack",
            "msgpack",
            "msgpack",
            ordered=True,
        )
        reference = read_file("example.msgpack")
        assert output == reference

    def test_toml2toml(self) -> None:
        output = self.convert_and_read("example.toml", "toml", "toml")
        reference = read_file("example.toml")
        assert toml_signature(output) == toml_signature(reference)

    def test_yaml2yaml(self) -> None:
        output = self.convert_and_read("example.yaml", "yaml", "yaml")
        reference = read_file("example.yaml")
        assert output == reference

    def test_cbor2cbor(self) -> None:
        output = self.convert_and_read("example.cbor", "cbor", "cbor")
        reference = read_file("example.cbor")
        self.assert_cbor_same(output, reference)

    def test_json2msgpack(self) -> None:
        def patch(x: Any) -> Any:
            x["owner"]["dob"] = datetime.datetime(1979, 5, 27, 7, 32)  # noqa: DTZ001
            return x

        output = self.convert_and_read(
            "example.json",
            "json",
            "msgpack",
            ordered=True,
            transform=patch,
        )
        reference = read_file("example.msgpack")
        assert output == reference

    def test_json2cbor(self) -> None:
        def patch(x: Any) -> Any:
            x["owner"]["dob"] = datetime.datetime(
                1979, 5, 27, 7, 32, 0, 0, datetime.timezone.utc
            )
            return x

        output = self.convert_and_read(
            "example.json",
            "json",
            "cbor",
            ordered=True,
            transform=patch,
        )

        reference = read_file("example.cbor")
        self.assert_cbor_same(output, reference)

    def test_json2toml(self) -> None:
        output = self.convert_and_read("example.json", "json", "toml").decode("utf-8")
        reference = read_file("example.toml").decode("utf-8")
        output_sig = toml_signature(output)
        # The date in 'example.json' is a string.
        reference_sig = toml_signature(
            reference.replace("1979-05-27T07:32:00Z", '"1979-05-27T07:32:00+00:00"')
        )
        assert output_sig == reference_sig

    def test_json2yaml(self) -> None:
        output = self.convert_and_read("example.json", "json", "yaml").decode("utf-8")
        reference = read_file("example.yaml").decode("utf-8")
        # The date in 'example.json' is a string.
        reference_patched = reference.replace(
            "1979-05-27 07:32:00+00:00", "'1979-05-27T07:32:00+00:00'"
        )
        assert output == reference_patched

    def test_msgpack2json(self) -> None:
        output = self.convert_and_read("example.msgpack", "msgpack", "json")
        reference = read_file("example.json")
        assert output == reference

    def test_msgpack2toml(self) -> None:
        output = self.convert_and_read("example.msgpack", "msgpack", "toml")
        reference = read_file("example.toml")
        assert toml_signature(output) == toml_signature(reference)

    def test_msgpack2yaml(self) -> None:
        output = self.convert_and_read("example.msgpack", "msgpack", "yaml")
        reference = read_file("example.yaml")
        assert output == reference

    def test_msgpack2cbor(self) -> None:
        output = self.convert_and_read(
            "example.msgpack",
            "msgpack",
            "cbor",
        )
        reference = read_file("example.cbor")
        self.assert_cbor_same(output, reference)

    def test_toml2json(self) -> None:
        output = self.convert_and_read("example.toml", "toml", "json")
        reference = read_file("example.json")
        assert output == reference

    def test_toml2msgpack(self) -> None:
        output = self.convert_and_read(
            "example.toml",
            "toml",
            "msgpack",
            transform=lambda col: remarshal.traverse(col, dict_callback=sorted_dict),
        )
        reference = read_file("example.msgpack")
        assert output == reference

    def test_toml2yaml(self) -> None:
        output = self.convert_and_read("example.toml", "toml", "yaml")
        reference = read_file("example.yaml")
        assert output == reference

    def test_toml2cbor(self) -> None:
        output = self.convert_and_read(
            "example.toml",
            "toml",
            "cbor",
        )
        reference = read_file("example.cbor")
        self.assert_cbor_same(output, reference)

    def test_yaml2json(self) -> None:
        output = self.convert_and_read("example.yaml", "yaml", "json")
        reference = read_file("example.json")
        assert output == reference

    def test_yaml2msgpack(self) -> None:
        output = self.convert_and_read(
            "example.yaml",
            "yaml",
            "msgpack",
            ordered=True,
        )
        reference = read_file("example.msgpack")
        assert output == reference

    def test_yaml2toml(self) -> None:
        output = self.convert_and_read("example.yaml", "yaml", "toml")
        reference = read_file("example.toml")
        assert toml_signature(output) == toml_signature(reference)

    def test_yaml2cbor(self) -> None:
        output = self.convert_and_read(
            "example.yaml",
            "yaml",
            "cbor",
        )
        reference = read_file("example.cbor")
        self.assert_cbor_same(output, reference)

    def test_cbor2json(self) -> None:
        output = self.convert_and_read("example.cbor", "cbor", "json")
        reference = read_file("example.json")
        assert output == reference

    def test_cbor2toml(self) -> None:
        output = self.convert_and_read("example.cbor", "cbor", "toml")
        reference = read_file("example.toml")
        output_sig = toml_signature(output)
        reference_sig = toml_signature(reference)
        assert output_sig == reference_sig

    def test_cbor2yaml(self) -> None:
        output = self.convert_and_read("example.cbor", "cbor", "yaml")
        reference = read_file("example.yaml")
        assert output == reference

    def test_cbor2msgpack(self) -> None:
        output = self.convert_and_read(
            "example.cbor",
            "cbor",
            "msgpack",
            ordered=True,
            transform=lambda col: remarshal.traverse(col, dict_callback=sorted_dict),
        )
        reference = read_file("example.msgpack")
        assert output == reference

    def test_missing_wrap(self) -> None:
        with pytest.raises(TypeError):
            self.convert_and_read("array.json", "json", "toml")

    def test_wrap(self) -> None:
        output = self.convert_and_read("array.json", "json", "toml", wrap="data")
        reference = read_file("array.toml")
        assert output == reference

    def test_unwrap(self) -> None:
        output = self.convert_and_read(
            "array.toml", "toml", "json", json_indent=None, unwrap="data"
        )
        reference = read_file("array.json")
        assert output == reference

    def test_malformed_json(self) -> None:
        with pytest.raises(ValueError):
            self.convert_and_read("garbage", "json", "yaml")

    def test_malformed_toml(self) -> None:
        with pytest.raises(ValueError):
            self.convert_and_read("garbage", "toml", "yaml")

    def test_malformed_yaml(self) -> None:
        with pytest.raises(ValueError):
            self.convert_and_read("garbage", "yaml", "json")

    def test_binary_to_json(self) -> None:
        with pytest.raises(ValueError):
            self.convert_and_read("bin.msgpack", "msgpack", "json")
        with pytest.raises(ValueError):
            self.convert_and_read("bin.yml", "yaml", "json")

    def test_binary_to_msgpack(self) -> None:
        self.convert_and_read("bin.yml", "yaml", "msgpack")

    def test_binary_to_toml(self) -> None:
        with pytest.raises(ValueError):
            self.convert_and_read("bin.msgpack", "msgpack", "toml")
        with pytest.raises(ValueError):
            self.convert_and_read("bin.yml", "yaml", "toml")

    def test_binary_to_yaml(self) -> None:
        self.convert_and_read("bin.msgpack", "msgpack", "yaml")

    def test_binary_to_cbor(self) -> None:
        self.convert_and_read("bin.msgpack", "msgpack", "cbor")

    def test_yaml_style_default(self) -> None:
        output = self.convert_and_read("long-line.json", "json", "yaml")
        reference = read_file("long-line-default.yaml")
        assert output == reference

    def test_yaml_style_single_quote(self) -> None:
        output = self.convert_and_read(
            "long-line.json", "json", "yaml", yaml_options={"default_style": "'"}
        )
        reference = read_file("long-line-single-quote.yaml")
        assert output == reference

    def test_yaml_style_double_quote(self) -> None:
        output = self.convert_and_read(
            "long-line.json", "json", "yaml", yaml_options={"default_style": '"'}
        )
        reference = read_file("long-line-double-quote.yaml")
        assert output == reference

    def test_yaml_style_pipe(self) -> None:
        output = self.convert_and_read(
            "long-line.json", "json", "yaml", yaml_options={"default_style": "|"}
        )
        reference = read_file("long-line-pipe.yaml")
        assert output == reference

    def test_yaml_style_gt(self) -> None:
        output = self.convert_and_read(
            "long-line.json", "json", "yaml", yaml_options={"default_style": ">"}
        )
        reference = read_file("long-line-gt.yaml")
        assert output == reference

    def test_argv0_to_format(self) -> None:
        def test_format_string(s: str) -> None:
            for from_str in "json", "toml", "yaml":
                for to_str in "json", "toml", "yaml":
                    from_parsed, to_parsed = remarshal.argv0_to_format(
                        s.format(from_str, to_str)
                    )
                    assert (from_parsed, to_parsed) == (from_str, to_str)

        test_format_string("{0}2{1}")
        test_format_string("{0}2{1}.exe")
        test_format_string("{0}2{1}-script.py")

    def test_format_detection(self) -> None:
        ext_to_fmt = {
            "json": "json",
            "toml": "toml",
            "yaml": "yaml",
            "yml": "yaml",
        }

        for from_ext in ext_to_fmt:
            for to_ext in ext_to_fmt:
                args = remarshal.parse_command_line(
                    [sys.argv[0], "input." + from_ext, "output." + to_ext]
                )

                assert args.input_format == ext_to_fmt[from_ext]
                assert args.output_format == ext_to_fmt[to_ext]

    def test_format_detection_failure_input_stdin(self) -> None:
        with pytest.raises(SystemExit) as cm:
            remarshal.parse_command_line([sys.argv[0], "-"])
        assert cm.value.code == 2

    def test_format_detection_failure_input_txt(self) -> None:
        with pytest.raises(SystemExit) as cm:
            remarshal.parse_command_line([sys.argv[0], "input.txt"])
        assert cm.value.code == 2

    def test_format_detection_failure_output_txt(self) -> None:
        with pytest.raises(SystemExit) as cm:
            remarshal.parse_command_line([sys.argv[0], "input.json", "output.txt"])
        assert cm.value.code == 2

    def test_run_no_args(self) -> None:
        with pytest.raises(SystemExit) as cm:
            remarshal.run([sys.argv[0]])
        assert cm.value.code == 2

    def test_run_help(self) -> None:
        with pytest.raises(SystemExit) as cm:
            remarshal.run([sys.argv[0], "--help"])
        assert cm.value.code == 0

    def test_run_no_input_file(self) -> None:
        args = [
            sys.argv[0],
            "-if",
            "json",
            "-of",
            "json",
            "fake-input-file-that-almost-certainly-doesnt-exist-2382",
        ]
        with pytest.raises(IOError) as cm:
            remarshal.run(args)
        assert cm.value.errno == errno.ENOENT

    def test_run_no_output_dir(self) -> None:
        args = [
            sys.argv[0],
            "-if",
            "json",
            "-of",
            "json",
            "-o",
            "this_path/almost-certainly/doesnt-exist-5836",
            data_file_path("example.json"),
        ]
        with pytest.raises(IOError) as cm:
            remarshal.run(args)
        assert cm.value.errno == errno.ENOENT

    def test_run_no_output_format(self) -> None:
        with pytest.raises(SystemExit) as cm:
            remarshal.run([sys.argv[0], data_file_path("array.toml")])
        assert cm.value.code == 2

    def test_run_short_commands(self) -> None:
        for output_format in ["cbor", "json", "msgpack", "toml", "yaml"]:
            remarshal.run(
                [f"json2{output_format}", "-i", data_file_path("example.json")]
            )

    def test_ordered_simple(self) -> None:
        formats = ("json", "toml", "yaml")
        for from_ in formats:
            for to in formats:
                output = self.convert_and_read(
                    "order." + from_, from_, to, ordered=True
                )
                reference = read_file("order." + to)

                message = "failed for {} to {} ({!r} instead of {!r})".format(
                    from_,
                    to,
                    output,
                    reference,
                )
                assert output == reference, message

    def test_ordered_yaml2yaml(self) -> None:
        output = self.convert_and_read("example.yaml", "yaml", "yaml", ordered=True)
        reference = read_file("example.yaml")
        assert output == reference

    def test_yaml2json_bool_null_key(self) -> None:
        output = self.convert_and_read(
            "bool-null-key.yaml",
            "yaml",
            "json",
            json_indent=0,
            ordered=True,
            stringify=True,
        )
        reference = read_file("bool-null-key.json")
        assert output == reference

    def test_yaml2toml_bool_null_key(self) -> None:
        output = self.convert_and_read(
            "bool-null-key.yaml",
            "yaml",
            "toml",
            ordered=True,
            stringify=True,
        )
        reference = read_file("bool-null-key.toml")
        assert output == reference

    def test_yaml2toml_timestamp_key(self) -> None:
        output = self.convert_and_read(
            "timestamp-key.yaml",
            "yaml",
            "toml",
            ordered=True,
            stringify=True,
        )
        reference = read_file("timestamp-key.toml")
        assert output == reference

    def test_yaml_width_default(self) -> None:
        output = self.convert_and_read(
            "long-line.json",
            "json",
            "yaml",
        ).decode("utf-8")
        assert len([char for char in output if char == "\n"]) == 4

    def test_yaml_width_30(self) -> None:
        output = self.convert_and_read(
            "long-line.json", "json", "yaml", yaml_options={"width": 5}
        ).decode("utf-8")
        assert len([char for char in output if char == "\n"]) == 21

    def test_yaml_width_120(self) -> None:
        output = self.convert_and_read(
            "long-line.json", "json", "yaml", yaml_options={"width": 120}
        ).decode("utf-8")
        assert len([char for char in output if char == "\n"]) == 3

    def test_yaml_ident_5(self) -> None:
        output = self.convert_and_read(
            "long-line.json", "json", "yaml", yaml_options={"indent": 5}
        ).decode("utf-8")
        assert set(re.findall(r"\n +", output)) == {"\n     ", "\n          "}

    def test_yaml2toml_empty_mapping(self) -> None:
        with pytest.raises(ValueError):
            self.convert_and_read("empty-mapping.yaml", "yaml", "toml")

    def test_yaml2toml_empty_mapping_stringify(self) -> None:
        output = self.convert_and_read(
            "empty-mapping.yaml",
            "yaml",
            "toml",
            stringify=True,
        )
        reference = read_file("empty-mapping.toml")
        assert output == reference

    def test_yaml2toml_numeric_key_null_value(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            self.convert_and_read(
                "numeric-key-null-value.yaml",
                "yaml",
                "toml",
            )
        exc_info.match("null value")

    def test_yaml2toml_numeric_key_null_value_stringify(self) -> None:
        output = self.convert_and_read(
            "numeric-key-null-value.yaml",
            "yaml",
            "toml",
            stringify=True,
        )
        reference = read_file("numeric-key-null-value.toml")
        assert output == reference

    def test_yaml_billion_laughs(self) -> None:
        with pytest.raises(remarshal.TooManyNodesError):
            self.convert_and_read("lol.yml", "yaml", "json")
