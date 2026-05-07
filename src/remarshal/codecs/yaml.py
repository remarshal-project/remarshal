from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING, ClassVar, cast

import ruamel.yaml
import ruamel.yaml.parser
import ruamel.yaml.representer
import ruamel.yaml.scalarstring
import ruamel.yaml.scanner

from remarshal.codec import Decoder, Encoder
from remarshal.options import FormatOptions, YAMLOptions, YAMLVersion

if TYPE_CHECKING:
    from remarshal.document import Document

UTF_8 = "utf-8"


def _format_to_version(format: str | None) -> YAMLVersion:
    match format:
        case "yaml-1.1":
            return (1, 1)
        case "yaml-1.2":
            return (1, 2)
    return None


class YAMLDecoder(Decoder):
    name: ClassVar[str] = "yaml"

    def decode(self, data: bytes, *, format: str | None = None) -> Document:
        try:
            yaml = ruamel.yaml.YAML(pure=True, typ="safe")
            yaml.version = _format_to_version(format)

            doc = yaml.load(data)
            return cast("Document", doc)
        except ruamel.yaml.YAMLError as e:
            problem = getattr(e, "problem", str(e))
            msg = f"Cannot parse as YAML ({problem})"
            raise ValueError(msg)


class YAMLEncoder(Encoder[YAMLOptions]):
    name: ClassVar[str] = "yaml"
    options_cls: ClassVar[type[FormatOptions]] = YAMLOptions

    def default_options(self) -> YAMLOptions:
        return YAMLOptions()

    def encode(self, data: Document, options: YAMLOptions) -> bytes:
        yaml = ruamel.yaml.YAML(pure=True)
        yaml.default_flow_style = False
        yaml.default_style = options.style  # type: ignore
        yaml.indent = options.indent
        yaml.version = options.version
        yaml.width = options.width

        if options.expand_aliases:
            yaml.representer.ignore_aliases = lambda *_: True

        style = options.style
        style_newline = options.style_newline

        def represent_none(self, data):
            return self.represent_scalar("tag:yaml.org,2002:null", "null")

        def represent_str(self, data):
            str_style = style_newline if "\n" in data else style
            return self.represent_scalar(
                "tag:yaml.org,2002:str", data, style=str_style
            )

        yaml.representer.add_representer(type(None), represent_none)
        yaml.representer.add_representer(str, represent_str)

        try:
            out = StringIO()
            yaml.dump(data, out)
            return out.getvalue().encode(UTF_8)
        except ruamel.yaml.YAMLError as e:
            problem = getattr(e, "problem", str(e))
            msg = f"Cannot convert data to YAML ({problem})"
            raise ValueError(msg)
