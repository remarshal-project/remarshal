from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING, ClassVar, cast

import ruamel.yaml
import ruamel.yaml.constructor
import ruamel.yaml.nodes
import ruamel.yaml.parser
import ruamel.yaml.representer
import ruamel.yaml.scalarstring
import ruamel.yaml.scanner

from remarshal.codec import Decoder, Encoder
from remarshal.document import TaggedValue
from remarshal.options import FormatOptions, YAMLOptions, YAMLVersion

if TYPE_CHECKING:
    from remarshal.document import Document

UTF_8 = "utf-8"


class YAMLDecoder(Decoder):
    """A YAML decoder pinned to a specific YAML version.

    Register one instance per supported version; the bare `YAMLDecoder()`
    with `version=None` lets `ruamel.yaml` pick its default.
    """

    name: ClassVar[str] = "yaml"

    def __init__(self, version: YAMLVersion = None) -> None:
        self.version = version

    def decode(self, data: bytes) -> Document:
        try:
            yaml = ruamel.yaml.YAML(pure=True, typ="safe")
            yaml.version = self.version

            def construct_tagged(
                constructor: ruamel.yaml.constructor.SafeConstructor,
                tag_suffix: str,
                node: ruamel.yaml.nodes.Node,
            ) -> TaggedValue:
                if isinstance(node, ruamel.yaml.nodes.ScalarNode):
                    value = constructor.construct_scalar(node)
                elif isinstance(node, ruamel.yaml.nodes.SequenceNode):
                    value = constructor.construct_sequence(node, deep=True)
                elif isinstance(node, ruamel.yaml.nodes.MappingNode):
                    value = constructor.construct_mapping(node, deep=True)
                else:
                    value = None
                return TaggedValue(node.tag, value)

            # Catch every tag without a registered constructor (any custom or
            # application tag such as `!secret`) and preserve it as a
            # `TaggedValue`. Standard tags like `!!str` are unaffected.
            yaml.constructor.add_multi_constructor("", construct_tagged)

            doc = yaml.load(data)
            return cast("Document", doc)
        except ruamel.yaml.YAMLError as e:
            problem = getattr(e, "problem", str(e))
            msg = f"Cannot parse as YAML ({problem})"
            raise ValueError(msg)


class YAMLEncoder(Encoder[YAMLOptions]):
    name: ClassVar[str] = "yaml"
    options_cls: ClassVar[type[FormatOptions]] = YAMLOptions

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
            return self.represent_scalar("tag:yaml.org,2002:str", data, style=str_style)

        def represent_tagged(self, data):
            node = self.represent_data(data.value)
            node.tag = data.tag
            return node

        yaml.representer.add_representer(type(None), represent_none)
        yaml.representer.add_representer(str, represent_str)
        yaml.representer.add_representer(TaggedValue, represent_tagged)

        try:
            out = StringIO()
            yaml.dump(data, out)
            return out.getvalue().encode(UTF_8)
        except ruamel.yaml.YAMLError as e:
            problem = getattr(e, "problem", str(e))
            msg = f"Cannot convert data to YAML ({problem})"
            raise ValueError(msg)
