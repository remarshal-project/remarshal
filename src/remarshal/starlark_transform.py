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

from starlark import (
    EvalError,
    Mutability,
    ResourceLimitExceeded,
    StarlarkSyntaxException,
    from_value,
    namespace,
    to_value,
)
from starlark import compile as starlark_compile

# === Predeclared `remarshal` helper module ===


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


def _make_remarshal_helpers() -> Any:
    """Return an opaque object exposing helper functions as attributes."""
    return namespace(
        "remarshal",
        {
            "bytes_to_str": b_bytes_to_str,
            "str_to_bytes": b_str_to_bytes,
            "bytes_len": b_bytes_len,
            "bytes_to_base64": b_bytes_to_base64,
            "base64_to_bytes": b_base64_to_bytes,
            "datetime_to_iso": b_datetime_to_iso,
            "iso_to_datetime": b_iso_to_datetime,
            "iso_to_date": b_iso_to_date,
            "iso_to_time": b_iso_to_time,
        },
    )


# === Top-level: `source` -> `transform` callable ===


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
    try:
        program = starlark_compile(source, filename=filename)
    except StarlarkSyntaxException as e:
        msg = f"Starlark syntax error: {e}"
        raise ValueError(msg) from e

    helpers = _make_remarshal_helpers()

    def transform(doc: Any) -> Any:
        # Build a fresh mutability scope for each call so successive runs
        # of the same compiled callable don't accumulate frozen state.
        mut = Mutability("remarshal")
        env = {"data": to_value(doc, mutability=mut), "remarshal": helpers}
        try:
            if program.is_expression:
                value = program.eval(
                    predeclared=env,
                    max_steps=max_steps,
                    max_allocs=max_allocs,
                )
            else:
                module = program.exec(
                    predeclared=env,
                    max_steps=max_steps,
                    max_allocs=max_allocs,
                )
                if "result" not in module.globals:
                    msg = (
                        "Starlark program must assign to top-level "
                        "'result' (e.g. `result = ...`)"
                    )
                    raise ValueError(msg)
                value = module.globals["result"]
        except ResourceLimitExceeded as e:
            msg = f"Starlark resource limit exceeded: {e}"
            raise ValueError(msg) from e
        except EvalError as e:
            msg = f"Starlark error: {e}"
            raise ValueError(msg) from e
        finally:
            mut.freeze()

        return from_value(value)

    return transform


__all__ = [
    "compile_transform",
]
