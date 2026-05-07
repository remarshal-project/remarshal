from __future__ import annotations

import datetime
import json as _json
from typing import Any, ClassVar, cast

from remarshal.codec import Decoder, Encoder
from remarshal.document import (
    Document,
    reject_special_keys,
    stringify_special_keys,
    traverse,
)
from remarshal.options import FormatOptions, JSONOptions

UTF_8 = "utf-8"


def _json_default_stringify(obj: Any) -> str:
    if isinstance(obj, (datetime.date, datetime.datetime, datetime.time)):
        return obj.isoformat()
    msg = f"{obj!r} is not JSON serializable"
    raise TypeError(msg)


class JSONDecoder(Decoder):
    name: ClassVar[str] = "json"

    def decode(self, data: bytes) -> Document:
        try:
            doc = _json.loads(data.decode(UTF_8))
            return cast("Document", doc)
        except _json.JSONDecodeError as e:
            msg = f"Cannot parse as JSON ({e})"
            raise ValueError(msg)


class JSONEncoder(Encoder[JSONOptions]):
    name: ClassVar[str] = "json"
    options_cls: ClassVar[type[FormatOptions]] = JSONOptions

    def default_options(self) -> JSONOptions:
        return JSONOptions()

    def encode(self, data: Document, options: JSONOptions) -> bytes:
        separators = (",", ": " if options.indent else ":")

        if options.stringify:
            default_callback = _json_default_stringify
            key_callback = stringify_special_keys
        else:
            default_callback = None
            key_callback = reject_special_keys

        try:
            text = (
                _json.dumps(
                    traverse(data, key_callback=key_callback),
                    default=default_callback,
                    ensure_ascii=False,
                    indent=options.indent,
                    separators=separators,
                    sort_keys=options.sort_keys,
                )
                + "\n"
            )
            return text.encode(UTF_8)
        except (TypeError, ValueError) as e:
            msg = f"Cannot convert data to JSON ({e})"
            raise ValueError(msg)
