from __future__ import annotations

import datetime
from typing import Any, Callable, Mapping, Sequence, Union

Document = Union[bool, bytes, datetime.datetime, Mapping, None, Sequence, str]


class TooManyValuesError(BaseException):
    pass


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


def reject_special_keys(key: Any) -> Any:
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


def stringify_special_keys(key: Any) -> Any:
    if isinstance(key, bool):
        return "true" if key else "false"
    if isinstance(key, (datetime.date, datetime.datetime, datetime.time)):
        return key.isoformat()
    if key is None:
        return "null"

    return str(key)


def validate_value_count(doc: Document, *, maximum: int) -> None:
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
