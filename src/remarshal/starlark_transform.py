# Remarshal, a utility to convert between serialization formats.
# Copyright (c) 2026 D. Bohdan
# License: MIT

"""Bridge between Remarshal's `Document` model and Starlark in Python.

Key facts that shape the bridge:

- Starlark in Python has no `bytes` and no datetime types; both are passed
  through opaquely. Helpers in the predeclared `remarshal` module let
  scripts inspect or rebuild them.
- Native Python `list`, `dict`, and `set` are not interoperable with the
  Starlark interpreter. We must wrap inputs in
  `StarlarkList` or `StarlarkDict`
  and unwrap outputs back to plain Python collections.
- Starlark in Python preserves dictionary insertion order, which matches
  Remarshal's order-preserving conversion.
- Starlark code that returns a `set`, a `range`, or a `tuple` is
  coerced to a plain `list` on the way out.
"""

from __future__ import annotations

import base64
import datetime
from typing import Any, Callable

import starlark
from starlark.eval import values as _values
from starlark.eval.module import Module
from starlark.syntax import parse, parse_expression
from starlark.syntax.errors import StarlarkSyntaxException


def _starlark_internals() -> tuple[Any, Any, Any, Any, Any, Any]:
    """Return `(Module, Dict, StarlarkList, StarlarkSet, Range, BuiltinFunction)`."""
    return (
        Module,
        _values.Dict,
        _values.StarlarkList,
        _values.StarlarkSet,
        _values.Range,
        _values.BuiltinFunction,
    )


# === Conversion in: `Document` -> Starlark wrappers ===


def _to_starlark(value: Any, mutability: Any, Dict_: Any, List_: Any) -> Any:
    match value:
        case None | bool() | int() | float() | str() | bytes():
            return value
        case datetime.datetime() | datetime.date() | datetime.time():
            return value
        case dict():
            items = {
                k: _to_starlark(v, mutability, Dict_, List_) for k, v in value.items()
            }
            return Dict_(items, mutability=mutability)
        case list() | tuple():
            return List_(
                [_to_starlark(v, mutability, Dict_, List_) for v in value],
                mutability=mutability,
            )
        case _:
            msg = f"cannot pass value of type {type(value).__name__!r} to Starlark"
            raise TypeError(msg)


# === Conversion out: Starlark wrappers -> `Document` ===


def _from_starlark(value: Any, Dict_: Any, List_: Any, Set_: Any, Range_: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return value
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value
    if isinstance(value, Dict_):
        return {
            _from_starlark(k, Dict_, List_, Set_, Range_): _from_starlark(
                v, Dict_, List_, Set_, Range_
            )
            for k, v in value._data.items()  # noqa: SLF001
        }
    if isinstance(value, List_):
        return [
            _from_starlark(v, Dict_, List_, Set_, Range_)
            for v in value._data  # noqa: SLF001
        ]
    if isinstance(value, tuple):
        return [_from_starlark(v, Dict_, List_, Set_, Range_) for v in value]
    if isinstance(value, Range_):
        return list(value)
    if isinstance(value, Set_):
        msg = (
            "Starlark transform returned a 'set'; "
            "convert it explicitly with sorted(s) or list(s)"
        )
        raise TypeError(msg)
    type_name = getattr(value, "_starlark_type", type(value).__name__)
    msg = f"Starlark transform returned a value of unsupported type {type_name!r}"
    raise TypeError(msg)


# === Predeclared `remarshal` helper module ===


def _make_remarshal_module(BuiltinFunction_: Any) -> Any:
    """Return an opaque object exposing helper functions as attributes."""

    def b_bytes_to_str(b: Any, encoding: str = "utf-8") -> str:
        if not isinstance(b, bytes):
            msg = f"remarshal.bytes_to_str: requires bytes, got {type(b).__name__!r}"
            raise TypeError(msg)
        if not isinstance(encoding, str):
            msg = "remarshal.bytes_to_str: encoding must be a string"
            raise TypeError(msg)
        return b.decode(encoding)

    def b_str_to_bytes(s: Any, encoding: str = "utf-8") -> bytes:
        if not isinstance(s, str):
            msg = f"remarshal.str_to_bytes: requires a string, got {type(s).__name__!r}"
            raise TypeError(msg)
        if not isinstance(encoding, str):
            msg = "remarshal.str_to_bytes: encoding must be a string"
            raise TypeError(msg)
        return s.encode(encoding)

    def b_bytes_len(b: Any) -> int:
        if not isinstance(b, bytes):
            msg = f"remarshal.bytes_len: requires bytes, got {type(b).__name__!r}"
            raise TypeError(msg)
        return len(b)

    def b_bytes_to_base64(b: Any) -> str:
        if not isinstance(b, bytes):
            msg = "remarshal.bytes_to_base64: requires bytes"
            raise TypeError(msg)
        return base64.b64encode(b).decode("ascii")

    def b_base64_to_bytes(s: Any) -> bytes:
        if not isinstance(s, str):
            msg = "remarshal.base64_to_bytes: requires a string"
            raise TypeError(msg)
        try:
            return base64.b64decode(s, validate=True)
        except Exception as e:
            msg = f"remarshal.base64_to_bytes: {e}"
            raise ValueError(msg)

    def b_datetime_to_iso(dt: Any) -> str:
        if not isinstance(dt, (datetime.datetime, datetime.date, datetime.time)):
            msg = (
                "remarshal.datetime_to_iso: requires a date, time, or "
                f"datetime, got {type(dt).__name__!r}"
            )
            raise TypeError(msg)
        return dt.isoformat()

    def b_iso_to_datetime(s: Any) -> datetime.datetime:
        if not isinstance(s, str):
            msg = "remarshal.iso_to_datetime: requires a string"
            raise TypeError(msg)
        try:
            return datetime.datetime.fromisoformat(s)
        except ValueError as e:
            msg = f"remarshal.iso_to_datetime: {e}"
            raise ValueError(msg)

    def b_iso_to_date(s: Any) -> datetime.date:
        if not isinstance(s, str):
            msg = "remarshal.iso_to_date: requires a string"
            raise TypeError(msg)
        try:
            return datetime.date.fromisoformat(s)
        except ValueError as e:
            msg = f"remarshal.iso_to_date: {e}"
            raise ValueError(msg)

    def b_iso_to_time(s: Any) -> datetime.time:
        if not isinstance(s, str):
            msg = "remarshal.iso_to_time: requires a string"
            raise TypeError(msg)
        try:
            return datetime.time.fromisoformat(s)
        except ValueError as e:
            msg = f"remarshal.iso_to_time: {e}"
            raise ValueError(msg)

    pairs = (
        ("bytes_to_str", b_bytes_to_str),
        ("str_to_bytes", b_str_to_bytes),
        ("bytes_len", b_bytes_len),
        ("bytes_to_base64", b_bytes_to_base64),
        ("base64_to_bytes", b_base64_to_bytes),
        ("datetime_to_iso", b_datetime_to_iso),
        ("iso_to_datetime", b_iso_to_datetime),
        ("iso_to_date", b_iso_to_date),
        ("iso_to_time", b_iso_to_time),
    )

    fields = {
        name: BuiltinFunction_(name=f"remarshal.{name}", impl=fn) for name, fn in pairs
    }

    class _Module:
        __slots__ = ("fields",)
        _starlark_type = "remarshal"

        def __init__(self, fields: dict[str, Any]) -> None:
            self.fields = fields

        def __repr__(self) -> str:
            return "<remarshal>"

    return _Module(fields)


# === Top-level: `source` -> `transform` callable ===


def _classify_source(source: str, filename: str) -> str:
    """Return `expr` or `program`, or raise `ValueError` on a syntax error.

    The classification rule: if the source parses as a single Starlark
    expression, it is classified as `expr`. Otherwise, it is validated as
    a program via `parse` and classified as `program`. If neither
    succeeds, the syntax error is raised.
    """
    try:
        parse_expression(source, file=filename)
    except (StarlarkSyntaxException, ValueError):
        pass
    else:
        return "expr"

    try:
        file = parse(source, file=filename)
    except (StarlarkSyntaxException, ValueError) as e:
        msg = f"Starlark syntax error: {e}"
        raise ValueError(msg)

    if file.errors:
        msg = f"Starlark syntax error: {file.errors[0]}"
        raise ValueError(msg)

    return "program"


def compile_transform(
    source: str,
    *,
    filename: str = "<starlark>",
    max_steps: int | None = 10_000_000,
    max_allocs: int | None = 128 * 1024 * 1024,
) -> Callable[[Any], Any]:
    """Compile `source` into a `transform(doc) -> doc` callable.

    `source` is auto-detected: if it parses as a single expression, it is
    treated as one and its value becomes the new document. Otherwise it is
    a Starlark program that must assign to a top-level name `result`.
    """
    Module_, Dict_, List_, Set_, Range_, BuiltinFunction_ = _starlark_internals()

    is_expr = _classify_source(source, filename) == "expr"

    helper_module = _make_remarshal_module(BuiltinFunction_)

    def transform(doc: Any) -> Any:
        # Build a fresh mutability scope for each call so successive runs
        # of the same compiled callable don't accumulate frozen state.
        module = Module_(filename)
        wrapped = _to_starlark(doc, module.mutability, Dict_, List_)
        # Universal namespace gets `data` and the `remarshal` helpers,
        # in addition to the standard builtins (`len`, `range`, `json`, ...).
        env = {"data": wrapped, "remarshal": helper_module}
        try:
            if is_expr:
                value = starlark.eval(
                    source,
                    filename=filename,
                    max_steps=max_steps,
                    max_allocs=max_allocs,
                    **env,
                )
            else:
                mod = starlark.exec_file(
                    source,
                    filename=filename,
                    universal=env,
                    max_steps=max_steps,
                    max_allocs=max_allocs,
                )
                if "result" not in mod.globals:
                    msg = (
                        "Starlark program must assign to top-level "
                        "'result' (e.g. `result = ...`)"
                    )
                    raise ValueError(msg)
                value = mod.globals["result"]
        except starlark.ResourceLimitExceeded as e:
            msg = f"Starlark resource limit exceeded: {e}"
            raise ValueError(msg)
        except starlark.EvalError as e:
            msg = f"Starlark error: {e}"
            raise ValueError(msg)
        except Exception as e:
            # Syntax errors and anything else from the interpreter.
            cls = type(e).__name__
            if cls in ("StarlarkSyntaxException", "StarlarkSyntaxError"):
                msg = f"Starlark syntax error: {e}"
                raise ValueError(msg)
            raise

        return _from_starlark(value, Dict_, List_, Set_, Range_)

    return transform


__all__ = [
    "compile_transform",
]
