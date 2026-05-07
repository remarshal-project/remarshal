from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

from remarshal.options import FormatOptions

if TYPE_CHECKING:
    from remarshal.document import Document

OptT = TypeVar("OptT", bound=FormatOptions)


class Decoder(ABC):
    """Parses a serialized format into a Document.

    `format` is the format alias under which the decoder was looked up.
    Most decoders ignore it; YAMLDecoder uses it to pick a YAML version.
    """

    name: ClassVar[str]

    @abstractmethod
    def decode(self, data: bytes, *, format: str | None = None) -> Document: ...


class Encoder(ABC, Generic[OptT]):
    """Serializes a Document into bytes for a given format."""

    name: ClassVar[str]
    options_cls: ClassVar[type[FormatOptions]]

    @abstractmethod
    def default_options(self) -> OptT: ...

    @abstractmethod
    def encode(self, data: Document, options: OptT) -> bytes: ...


DECODERS: dict[str, Decoder] = {}
ENCODERS: dict[str, Encoder[Any]] = {}


def register_decoder(decoder: Decoder, *aliases: str) -> None:
    DECODERS[decoder.name] = decoder
    for alias in aliases:
        DECODERS[alias] = decoder


def register_encoder(encoder: Encoder[Any], *aliases: str) -> None:
    ENCODERS[encoder.name] = encoder
    for alias in aliases:
        ENCODERS[alias] = encoder


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
    return get_decoder(input_format).decode(input_data, format=input_format)


def encode(
    output_format: str,
    data: Document,
    *,
    options: FormatOptions | None,
) -> bytes:
    encoder = get_encoder(output_format)

    if options is None:
        options = encoder.default_options()
    elif not isinstance(options, encoder.options_cls):
        msg = (
            f"expected 'options' argument to have class "
            f"'{encoder.options_cls.__name__}'"
        )
        raise TypeError(msg)

    return encoder.encode(data, options)
