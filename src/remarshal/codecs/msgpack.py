from __future__ import annotations

import datetime
from typing import ClassVar, cast

import umsgpack

from remarshal.codec import Decoder, Encoder
from remarshal.document import Document, traverse
from remarshal.options import FormatOptions, MsgPackOptions


def _reject_local_datetime(obj: datetime.datetime) -> None:
    if obj.tzinfo is None:
        msg = "'datetime.datetime' without a time zone is unsupported"
        raise TypeError(msg)


class MsgPackDecoder(Decoder):
    name: ClassVar[str] = "msgpack"

    def decode(self, data: bytes, *, format: str | None = None) -> Document:
        try:
            doc = umsgpack.unpackb(data)
            return cast("Document", doc)
        except umsgpack.UnpackException as e:
            msg = f"Cannot parse as MessagePack ({e})"
            raise ValueError(msg)


class MsgPackEncoder(Encoder[MsgPackOptions]):
    name: ClassVar[str] = "msgpack"
    options_cls: ClassVar[type[FormatOptions]] = MsgPackOptions

    def default_options(self) -> MsgPackOptions:
        return MsgPackOptions()

    def encode(self, data: Document, options: MsgPackOptions) -> bytes:
        try:
            traverse(
                data,
                instance_callbacks=[(datetime.datetime, _reject_local_datetime)],
            )
            return umsgpack.packb(data)
        except (TypeError, umsgpack.UnsupportedTypeException) as e:
            msg = f"Cannot convert data to MessagePack ({e})"
            raise ValueError(msg)
