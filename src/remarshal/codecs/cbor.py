from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

import cbor2  # type: ignore

from remarshal.codec import Decoder, Encoder
from remarshal.options import CBOROptions, FormatOptions

if TYPE_CHECKING:
    from remarshal.document import Document


class CBORDecoder(Decoder):
    name: ClassVar[str] = "cbor"

    def decode(self, data: bytes) -> Document:
        try:
            doc = cbor2.loads(data)
            return cast("Document", doc)
        except cbor2.CBORDecodeError as e:
            msg = f"Cannot parse as CBOR ({e})"
            raise ValueError(msg)


class CBOREncoder(Encoder[CBOROptions]):
    name: ClassVar[str] = "cbor"
    options_cls: ClassVar[type[FormatOptions]] = CBOROptions

    def encode(self, data: Document, options: CBOROptions) -> bytes:
        try:
            return bytes(cbor2.dumps(data))
        except cbor2.CBOREncodeError as e:
            msg = f"Cannot convert data to CBOR ({e})"
            raise ValueError(msg)
