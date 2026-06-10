from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence, Union


@dataclass(frozen=True)
class TaggedValue:
    """A value annotated with a YAML tag.

    This is the in-memory representation of a YAML tag such as `!secret`.
    Formats without a native concept of tags (every format other than YAML)
    represent it on the wire as a single-key mapping whose key is the tag,
    for example `{"!secret": "password"}`.
    The conversion between this type and that envelope
    is controlled by the `--yaml-tags` option;
    see `tags_to_envelopes` and `envelopes_to_tags`.
    """

    tag: str
    value: "Document"


Document = Union[
    bool,
    bytes,
    datetime.datetime,
    float,
    int,
    Mapping,
    None,
    Sequence,
    str,
    TaggedValue,
]


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
    """Recursively traverse a `Document` and apply callbacks to its elements."""
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
    elif isinstance(col, TaggedValue):
        res = TaggedValue(
            col.tag,
            traverse(
                col.value,
                dict_callback,
                list_callback,
                key_callback,
                instance_callbacks,
                default_callback,
            ),
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


def tags_to_envelopes(doc: Any) -> Any:
    """Replace every `TaggedValue` with its on-the-wire mapping envelope.

    `TaggedValue("!secret", "password")` becomes `{"!secret": "password"}`.
    Use this before encoding to a format without native tags.
    """
    if isinstance(doc, TaggedValue):
        return {doc.tag: tags_to_envelopes(doc.value)}
    if isinstance(doc, dict):
        return {k: tags_to_envelopes(v) for k, v in doc.items()}
    if isinstance(doc, list):
        return [tags_to_envelopes(x) for x in doc]
    return doc


def envelopes_to_tags(doc: Any) -> Any:
    """Replace every tag envelope mapping with a `TaggedValue`.

    A mapping with a single key that is a string starting with `!` is treated
    as an envelope: `{"!secret": "password"}` becomes
    `TaggedValue("!secret", "password")`. Use this before encoding to YAML so
    the tag is emitted natively.
    """
    if isinstance(doc, TaggedValue):
        return TaggedValue(doc.tag, envelopes_to_tags(doc.value))
    if isinstance(doc, dict):
        converted = {k: envelopes_to_tags(v) for k, v in doc.items()}
        if len(converted) == 1:
            ((key, value),) = converted.items()
            if isinstance(key, str) and key.startswith("!"):
                return TaggedValue(key, value)
        return converted
    if isinstance(doc, list):
        return [envelopes_to_tags(x) for x in doc]
    return doc


def contains_tagged_value(doc: Any) -> bool:
    """Report whether `doc` contains a `TaggedValue` anywhere within it."""
    if isinstance(doc, TaggedValue):
        return True
    if isinstance(doc, dict):
        return any(contains_tagged_value(v) for v in doc.values())
    if isinstance(doc, list):
        return any(contains_tagged_value(x) for x in doc)
    return False


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
