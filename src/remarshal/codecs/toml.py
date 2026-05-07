from __future__ import annotations

from typing import Any, ClassVar, Mapping, cast

import tomli as tomllib
import tomlkit
import tomlkit.items

from remarshal.codec import Decoder, Encoder
from remarshal.document import (
    Document,
    reject_special_keys,
    stringify_special_keys,
    traverse,
)
from remarshal.options import FormatOptions, TOMLOptions

UTF_8 = "utf-8"


class TOMLDecoder(Decoder):
    name: ClassVar[str] = "toml"

    def decode(self, data: bytes, *, format: str | None = None) -> Document:
        try:
            doc = tomllib.loads(data.decode(UTF_8))
            return cast("Document", doc)
        except tomllib.TOMLDecodeError as e:
            msg = f"Cannot parse as TOML ({e})"
            raise ValueError(msg)


class TOMLEncoder(Encoder[TOMLOptions]):
    name: ClassVar[str] = "toml"
    options_cls: ClassVar[type[FormatOptions]] = TOMLOptions

    def default_options(self) -> TOMLOptions:
        return TOMLOptions()

    def encode(self, data: Document, options: TOMLOptions) -> bytes:
        if not isinstance(data, Mapping):
            msg = (
                f"Top-level value of type '{type(data).__name__}' cannot "
                "be encoded as TOML"
            )
            raise TypeError(msg)

        key_callback = (
            stringify_special_keys if options.stringify else reject_special_keys
        )

        def reject_null(x: Any) -> Any:
            if x is None:
                msg = "null values are not supported"
                raise TypeError(msg)
            return x

        def stringify_null(x: Any) -> Any:
            if x is None:
                return "null"
            return x

        default_callback = stringify_null if options.stringify else reject_null

        try:
            toml = tomlkit.item(
                traverse(
                    data,
                    key_callback=key_callback,
                    default_callback=default_callback,
                ),
                _sort_keys=options.sort_keys,
            )

            def multilinify(item: tomlkit.items.Item) -> None:
                match item:
                    case tomlkit.items.Array():
                        if len(item) >= options.multiline_threshold:
                            item.multiline(multiline=True)

                    case tomlkit.items.AbstractTable():
                        for value in item.values():
                            multilinify(value)

            multilinify(toml)

            return toml.as_string().encode(UTF_8)
        except AttributeError as e:
            if str(e) == "'list' object has no attribute 'as_string'":
                msg = (
                    "Cannot convert non-dictionary data to TOML; "
                    'use "--wrap" to wrap it in a dictionary'
                )
                raise ValueError(msg)
            else:
                raise e
        except (TypeError, ValueError) as e:
            msg = f"Cannot convert data to TOML ({e})"
            raise ValueError(msg)
