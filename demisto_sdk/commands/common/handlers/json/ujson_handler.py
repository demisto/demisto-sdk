from typing import IO, Any, AnyStr

import ujson  # noqa: TID251 - this is the handler

from demisto_sdk.commands.common.handlers.xsoar_handler import (
    JSONDecodeError,
    XSOAR_Handler,
)


class UJSON_Handler(XSOAR_Handler):
    """
    XSOAR wrapper to UJSON
    Use only this wrapper for json handling.
    """

    JSONDecodeError = JSONDecodeError

    def __init__(self):
        self.json = ujson

    def loads(self, s: AnyStr):
        try:
            return self.json.loads(s)
        except ValueError as e:
            raise JSONDecodeError(f"input: {s!r}, error: {e}") from e

    def load(self, fp: IO[str]):
        try:
            return self.json.load(fp)
        except ValueError as e:
            raise JSONDecodeError(e)

    def dump(self, data: Any, fp: IO[str], indent=0, sort_keys=False, **kwargs):
        try:
            self.json.dump(
                data,
                fp,
                indent=indent,
                sort_keys=sort_keys,
                escape_forward_slashes=kwargs.get("escape_forward_slashes", False),
                encode_html_chars=kwargs.get("encode_html_chars", False),
                ensure_ascii=kwargs.get("ensure_ascii", False),
            )
        except ValueError as e:
            raise JSONDecodeError(e) from e

    def dumps(self, obj: Any, indent=0, sort_keys=False, **kwargs):
        try:
            return self.json.dumps(
                obj,
                indent=indent,
                sort_keys=sort_keys,
                escape_forward_slashes=kwargs.get("escape_forward_slashes", False),
                ensure_ascii=kwargs.get("ensure_ascii", False),
            )
        except ValueError as e:
            raise JSONDecodeError(e) from e
