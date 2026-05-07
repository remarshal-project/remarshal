from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

from remarshal.options import FormatOptions

if TYPE_CHECKING:
    from remarshal.document import Document

OptT = TypeVar("OptT", bound=FormatOptions)


class Decoder(ABC):
    """Abstract base class for decoders
    that parse a serialized format into a `Document`."""

    name: ClassVar[str]

    @abstractmethod
    def decode(self, data: bytes) -> Document: ...


class Encoder(ABC, Generic[OptT]):
    """Serialize a `Document` into bytes for a given format.

    `options_cls` is used by the `encode()` function as a runtime type check
    and as a factory to build default options when
    the caller passes `options=None`.
    Every `FormatOptions` subclass has defaults for all its fields,
    so `options_cls()` always succeeds.
    """

    name: ClassVar[str]
    options_cls: ClassVar[type[FormatOptions]]

    @abstractmethod
    def encode(self, data: Document, options: OptT) -> bytes: ...


DECODERS: dict[str, Decoder] = {}
ENCODERS: dict[str, Encoder[Any]] = {}


def register_decoder(decoder: Decoder, *names: str) -> None:
    """Register `decoder` under each of `names`, defaulting to `decoder.name`."""
    if not names:
        names = (decoder.name,)
    for name in names:
        DECODERS[name] = decoder


def register_encoder(encoder: Encoder[Any], *names: str) -> None:
    """Register `encoder` under each of `names`, defaulting to `encoder.name`."""
    if not names:
        names = (encoder.name,)
    for name in names:
        ENCODERS[name] = encoder


def get_decoder(format: str) -> Decoder:
    try:
        return DECODERS[format]
    except KeyError:
        msg = f"Unknown input format: {format}"
        raise ValueError(msg)


def get_encoder(format: str) -> Encoder[Any]:
    try:
        return ENCODERS[format]
    except KeyError:
        msg = f"Unknown output format: {format}"
        raise ValueError(msg)


def decode(input_format: str, input_data: bytes) -> Document:
    return get_decoder(input_format).decode(input_data)


def encode(
    output_format: str,
    data: Document,
    *,
    options: FormatOptions | None,
) -> bytes:
    encoder = get_encoder(output_format)

    if options is None:
        options = encoder.options_cls()
    elif not isinstance(options, encoder.options_cls):
        msg = (
            f"expected 'options' argument to have class "
            f"'{encoder.options_cls.__name__}'"
        )
        raise TypeError(msg)

    return encoder.encode(data, options)
