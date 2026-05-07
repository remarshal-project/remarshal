"""`Encoder` and `Decoder` classes for each supported format.

Importing this package registers every built-in codec in the
`remarshal.codec` registries `DECODERS` and `ENCODERS`.
"""

from __future__ import annotations

from remarshal.codec import register_decoder, register_encoder
from remarshal.codecs.cbor import CBORDecoder, CBOREncoder
from remarshal.codecs.json import JSONDecoder, JSONEncoder
from remarshal.codecs.msgpack import MsgPackDecoder, MsgPackEncoder
from remarshal.codecs.python import PythonEncoder
from remarshal.codecs.toml import TOMLDecoder, TOMLEncoder
from remarshal.codecs.yaml import YAMLDecoder, YAMLEncoder

__all__ = [
    "CBORDecoder",
    "CBOREncoder",
    "JSONDecoder",
    "JSONEncoder",
    "MsgPackDecoder",
    "MsgPackEncoder",
    "PythonEncoder",
    "TOMLDecoder",
    "TOMLEncoder",
    "YAMLDecoder",
    "YAMLEncoder",
]


def _register_all() -> None:
    register_decoder(CBORDecoder())
    register_decoder(JSONDecoder())
    register_decoder(MsgPackDecoder())
    register_decoder(TOMLDecoder())
    register_decoder(YAMLDecoder())
    register_decoder(YAMLDecoder((1, 1)), "yaml-1.1")
    register_decoder(YAMLDecoder((1, 2)), "yaml-1.2")

    register_encoder(CBOREncoder())
    register_encoder(JSONEncoder())
    register_encoder(MsgPackEncoder())
    register_encoder(PythonEncoder())
    register_encoder(TOMLEncoder())
    register_encoder(YAMLEncoder(), "yaml", "yaml-1.1", "yaml-1.2")


_register_all()
