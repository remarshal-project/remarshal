# Remarshal, a utility to convert between serialization formats.
# Copyright (c) 2014-2020, 2024-2026 D. Bohdan
# License: MIT

"""Tests for the optional Starlark transform feature.

These tests are skipped if the `starlark` package isn't installed.
"""

from __future__ import annotations

import datetime
import json
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import starlark

import remarshal
from remarshal.main import _parse_command_line

if TYPE_CHECKING:
    from collections.abc import Callable


from remarshal.starlark_transform import (  # noqa: E402
    compile_transform,
)

TEST_PATH = Path(__file__).resolve().parent


def data_file_path(filename: str) -> str:
    if filename.startswith("example."):
        return str(TEST_PATH.parent / filename)
    return str(TEST_PATH / filename)


def read_file(filename: str) -> bytes:
    return Path(data_file_path(filename)).read_bytes()


@pytest.fixture
def convert_and_read(tmp_path):
    def _convert(  # noqa: PLR0913
        input_filename: str,
        input_format: str,
        output_format: str,
        *,
        starlark_code: str | None = None,
        starlark_file: str | None = None,
        starlark_max_steps: int | None = None,
        starlark_max_allocs: int | None = None,
        unwrap: str | None = None,
        wrap: str | None = None,
        stringify: bool = False,
    ) -> bytes:
        out_path = tmp_path / secrets.token_hex(16)
        options = remarshal.format_options(output_format, stringify=stringify)
        transform: Callable[[Any], Any] | None = None
        if starlark_code is not None:
            transform = compile_transform(
                starlark_code,
                max_steps=starlark_max_steps,
                max_allocs=starlark_max_allocs,
            )
        elif starlark_file is not None:
            transform = compile_transform(
                Path(starlark_file).read_text(encoding="utf-8"),
                filename=starlark_file,
                max_steps=starlark_max_steps,
                max_allocs=starlark_max_allocs,
            )
        remarshal.remarshal(
            input_format,
            output_format,
            data_file_path(input_filename),
            str(out_path),
            options=options,
            transform=transform,
            unwrap=unwrap,
            wrap=wrap,
        )
        return out_path.read_bytes()

    return _convert


# === Compile / parse mode auto-detection ===


class TestCompile:
    def test_expression_mode(self) -> None:
        f = compile_transform("data + 1")
        assert f(41) == 42

    def test_program_mode_with_result(self) -> None:
        f = compile_transform("x = data * 2\nresult = x + 1")
        assert f(10) == 21

    def test_program_mode_missing_result(self) -> None:
        f = compile_transform("x = data * 2")
        with pytest.raises(ValueError, match="must assign to top-level 'result'"):
            f(10)

    def test_syntax_error(self) -> None:
        with pytest.raises(ValueError, match="Starlark syntax error"):
            compile_transform("def (")

    def test_def_function_then_call(self) -> None:
        # Expression mode after def: this is a program (def is a statement),
        # so the user must wire it up via 'result'.
        f = compile_transform("def double(x):\n    return x * 2\nresult = double(data)")
        assert f(5) == 10


# === Type round-tripping ===


class TestTypes:
    def test_identity_primitives(self) -> None:
        f = compile_transform("data")
        for v in (None, True, False, 0, 1, -1, 3.14, "hello", "", "Тест"):
            assert f(v) == v, v

    def test_big_int(self) -> None:
        f = compile_transform("data * 2")
        assert f(10**40) == 2 * 10**40

    def test_dict_round_trip_preserves_order(self) -> None:
        f = compile_transform("data")
        d = {"b": 1, "a": 2, "c": 3}
        out = f(d)
        assert isinstance(out, dict)
        assert list(out.keys()) == ["b", "a", "c"]

    def test_dict_keys_are_native_python(self) -> None:
        f = compile_transform("data")
        d = {"a": 1}
        out = f(d)
        assert type(out) is dict

    def test_list_round_trip(self) -> None:
        f = compile_transform("data")
        out = f([1, 2, [3, 4]])
        assert out == [1, 2, [3, 4]]
        assert type(out) is list
        assert type(out[2]) is list

    def test_tuple_returned_becomes_list(self) -> None:
        f = compile_transform("(1, 2, 3)")
        out = f(None)
        assert out == [1, 2, 3]
        assert isinstance(out, list)

    def test_range_returned_becomes_list(self) -> None:
        f = compile_transform("range(3)")
        assert f(None) == [0, 1, 2]

    def test_set_returned_is_rejected(self) -> None:
        f = compile_transform("set([1, 2, 3])")
        with pytest.raises(TypeError, match="got a Starlark set"):
            f(None)

    def test_set_can_be_converted_in_starlark(self) -> None:
        f = compile_transform("sorted(set([3, 1, 2]))")
        assert f(None) == [1, 2, 3]

    # --- bytes ---

    def test_bytes_passthrough(self) -> None:
        f = compile_transform("data")
        out = f(b"hello \x00 world")
        assert out == b"hello \x00 world"
        assert isinstance(out, bytes)

    def test_bytes_inside_collection(self) -> None:
        f = compile_transform("data")
        out = f({"k": b"\xff\xfe"})
        assert out == {"k": b"\xff\xfe"}

    def test_bytes_to_str_helper(self) -> None:
        f = compile_transform("remarshal.bytes_to_str(data)")
        assert f(b"hello") == "hello"

    def test_str_to_bytes_helper(self) -> None:
        f = compile_transform("remarshal.str_to_bytes(data)")
        out = f("hello")
        assert out == b"hello"
        assert isinstance(out, bytes)

    def test_bytes_len_helper(self) -> None:
        f = compile_transform("remarshal.bytes_len(data)")
        assert f(b"\x00\x01\x02") == 3

    def test_base64_round_trip(self) -> None:
        f = compile_transform(
            "remarshal.base64_to_bytes(remarshal.bytes_to_base64(data))"
        )
        assert f(b"\x00\x01binary\xff") == b"\x00\x01binary\xff"

    def test_bytes_len_rejects_non_bytes(self) -> None:
        f = compile_transform("remarshal.bytes_len(data)")
        with pytest.raises(ValueError, match="requires bytes"):
            f("not bytes")

    # --- datetime / date / time ---

    def test_datetime_passthrough(self) -> None:
        f = compile_transform("data")
        dt = datetime.datetime(2024, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
        assert f(dt) == dt

    def test_date_passthrough(self) -> None:
        f = compile_transform("data")
        d = datetime.date(2024, 1, 2)
        assert f(d) == d

    def test_time_passthrough(self) -> None:
        f = compile_transform("data")
        t = datetime.time(12, 34, 56)
        assert f(t) == t

    def test_datetime_to_iso_helper(self) -> None:
        f = compile_transform("remarshal.datetime_to_iso(data)")
        dt = datetime.datetime(2024, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
        assert f(dt) == "2024-01-02T03:04:05+00:00"

    def test_date_to_iso_helper(self) -> None:
        f = compile_transform("remarshal.datetime_to_iso(data)")
        assert f(datetime.date(2024, 1, 2)) == "2024-01-02"

    def test_time_to_iso_helper(self) -> None:
        f = compile_transform("remarshal.datetime_to_iso(data)")
        assert f(datetime.time(1, 2, 3)) == "01:02:03"

    def test_iso_to_datetime_helper(self) -> None:
        f = compile_transform("remarshal.iso_to_datetime(data)")
        out = f("2024-01-02T03:04:05+00:00")
        assert out == datetime.datetime(
            2024, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc
        )

    def test_iso_to_date_helper(self) -> None:
        f = compile_transform("remarshal.iso_to_date(data)")
        assert f("2024-01-02") == datetime.date(2024, 1, 2)

    def test_iso_to_time_helper(self) -> None:
        f = compile_transform("remarshal.iso_to_time(data)")
        assert f("12:34:56") == datetime.time(12, 34, 56)

    def test_replace_datetime_with_string(self) -> None:
        # User wants to stringify a datetime so it can be JSON-encoded.
        f = compile_transform(
            "{k: remarshal.datetime_to_iso(v) for k, v in data.items()}"
        )
        dt = datetime.datetime(2024, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
        out = f({"created": dt})
        assert out == {"created": "2024-01-02T03:04:05+00:00"}

    # --- key types ---

    def test_dict_with_bool_key(self) -> None:
        f = compile_transform("data")
        out = f({True: "yes", False: "no"})
        assert out == {True: "yes", False: "no"}

    def test_dict_with_none_key(self) -> None:
        f = compile_transform("data")
        out = f({None: "n", "a": "b"})
        assert out == {None: "n", "a": "b"}

    def test_dict_with_int_key(self) -> None:
        f = compile_transform("data")
        out = f({1: "a", 2: "b"})
        assert out == {1: "a", 2: "b"}


# === Operations ===


class TestTransform:
    def test_filter_list(self) -> None:
        f = compile_transform("[x for x in data if x % 2 == 0]")
        assert f([1, 2, 3, 4, 5]) == [2, 4]

    def test_map_dict(self) -> None:
        f = compile_transform("{k: v * 2 for k, v in data.items()}")
        assert f({"a": 1, "b": 2}) == {"a": 2, "b": 4}

    def test_sorted_keys(self) -> None:
        f = compile_transform("{k: data[k] for k in sorted(data)}")
        out = f({"c": 3, "a": 1, "b": 2})
        assert list(out.keys()) == ["a", "b", "c"]

    def test_json_module_available(self) -> None:
        f = compile_transform("json.decode(json.encode(data))")
        out = f({"a": [1, 2, 3]})
        assert out == {"a": [1, 2, 3]}


# === Resource limits ===


class TestLimits:
    def test_step_limit(self) -> None:
        # Tight cap that a non-trivial sum will blow.
        f = compile_transform(
            "sum([i*i for i in range(10000)])",
            max_steps=100,
        )
        with pytest.raises(ValueError, match="resource limit"):
            f(None)

    def test_alloc_limit(self) -> None:
        f = compile_transform(
            "[0] * 100000",
            max_allocs=4096,
        )
        with pytest.raises(ValueError, match="resource limit"):
            f(None)

    def test_unlimited_via_none(self) -> None:
        f = compile_transform(
            "sum([i for i in range(1000)])",
            max_steps=None,
            max_allocs=None,
        )
        assert f(None) == sum(range(1000))


# === EvalError handling ===


class TestErrors:
    def test_runtime_error_wrapped(self) -> None:
        f = compile_transform("1 + 'x'")
        with pytest.raises(ValueError, match="Starlark error"):
            f(None)

    def test_undefined_name(self) -> None:
        f = compile_transform("does_not_exist")
        with pytest.raises(ValueError):
            f(None)


# === End-to-end: data through the actual format pipeline ===


class TestPipeline:
    def test_json_to_json_filter(self, convert_and_read) -> None:
        # multiline.json has 'foo', 'bar', 'baz' top-level keys.
        out = convert_and_read(
            "multiline.json",
            "json",
            "json",
            starlark_code='{"foo": data["foo"]}',
        )
        assert json.loads(out) == {"foo": [1, 2, [3], 4, 5]}

    def test_yaml_to_json_with_datetime_stringify(self, convert_and_read) -> None:
        out = convert_and_read(
            "datetime-tz.toml",
            "toml",
            "json",
            starlark_code=(
                "{k: remarshal.datetime_to_iso(v) for k, v in data.items()}"
            ),
        )
        assert json.loads(out) == {"foo": "2012-12-12T12:34:56+00:00"}

    def test_msgpack_to_yaml_filter_bytes(self, convert_and_read) -> None:
        # bin.yml encodes binary fields. Filter to only one key.
        out = convert_and_read(
            "bin.yml",
            "yaml",
            "yaml",
            starlark_code='{"hosts": data["clients"]["hosts"]}',
        )
        assert b"alpha" in out or b"YWxwaGE" in out

    def test_msgpack_bytes_to_str(self, convert_and_read) -> None:
        out = convert_and_read(
            "bin.yml",
            "yaml",
            "json",
            starlark_code=(
                '{  "owner_name":     remarshal.bytes_to_str(data["owner"]["name"])}'
            ),
        )
        assert json.loads(out) == {"owner_name": "Tom Preston-Werner"}

    def test_unwrap_then_transform(self, convert_and_read) -> None:
        # array.toml has a top-level table 'data' wrapping a list.
        out = convert_and_read(
            "array.toml",
            "toml",
            "json",
            unwrap="data",
            starlark_code="[item for item in data if type(item) == 'dict']",
        )
        # The fixture is [{"a":"b"},{"c":[1,2,3]}].
        assert json.loads(out) == [{"a": "b"}, {"c": [1, 2, 3]}]

    def test_transform_then_wrap(self, convert_and_read) -> None:
        # Wrap pre-transform: transform sees the wrapped dict.
        out = convert_and_read(
            "array.json",
            "json",
            "toml",
            wrap="items",
            starlark_code="data",
        )
        # Output should be valid TOML with [[items]] tables.
        assert b"[[items]]" in out

    def test_transform_replacing_top_level_array(self, convert_and_read) -> None:
        out = convert_and_read(
            "array.json",
            "json",
            "json",
            starlark_code="[x for x in data if 'a' in x]",
        )
        assert json.loads(out) == [{"a": "b"}]


# === CLI argument parsing ===


class TestCLI:
    def _argv(self, *extra: str) -> list[str]:
        return ["remarshal", "-f", "json", "-t", "json", *extra]

    def test_starlark_flag(self) -> None:
        ns = _parse_command_line(self._argv("--starlark", "data"))
        assert ns.starlark == "data"
        assert ns.starlark_file is None

    def test_starlark_file_flag(self) -> None:
        ns = _parse_command_line(self._argv("--starlark-file", "x.star"))
        assert ns.starlark is None
        assert ns.starlark_file == "x.star"

    def test_mutually_exclusive(self) -> None:
        with pytest.raises(SystemExit):
            _parse_command_line(
                self._argv("--starlark", "data", "--starlark-file", "x.star")
            )

    def test_default_limits_present(self) -> None:
        ns = _parse_command_line(self._argv())
        assert ns.starlark_max_steps == 10_000_000
        assert ns.starlark_max_allocs == 128 * 1024 * 1024

    def test_starlark_file_loaded(self, tmp_path) -> None:
        script = tmp_path / "transform.star"
        script.write_text(
            "result = {k: v + 1 for k, v in data.items()}\n",
            encoding="utf-8",
        )
        f = compile_transform(
            script.read_text(encoding="utf-8"),
            filename=str(script),
        )
        assert f({"a": 1, "b": 2}) == {"a": 2, "b": 3}
