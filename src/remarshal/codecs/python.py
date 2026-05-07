from __future__ import annotations

import pprint
from typing import TYPE_CHECKING, ClassVar

from remarshal.codec import Encoder
from remarshal.options import FormatOptions, PythonOptions

if TYPE_CHECKING:
    from remarshal.document import Document

UTF_8 = "utf-8"


class PythonEncoder(Encoder[PythonOptions]):
    name: ClassVar[str] = "python"
    options_cls: ClassVar[type[FormatOptions]] = PythonOptions

    def default_options(self) -> PythonOptions:
        return PythonOptions()

    def encode(self, data: Document, options: PythonOptions) -> bytes:
        if options.indent is None:
            code = repr(data)
        else:
            code = pprint.pformat(
                data,
                indent=options.indent,
                sort_dicts=options.sort_keys,
                width=options.width,
            )

        return (code + "\n").encode(UTF_8)
