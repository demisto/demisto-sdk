from typing import IO, Any, AnyStr

import json5  # - this is the handler

from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler


class JSONDecodeError(ValueError):
    pass


class JSON5_Handler(XSOAR_Handler):
    """
    XSOAR wrapper to JSON5
    Use only this wrapper for json handling.
    """

    JSONDecodeError = JSONDecodeError

    def __init__(self):
        self.json = json5

    def loads(self, s: AnyStr):
        try:
            return self.json.loads(s)
        except ValueError as e:
            raise JSONDecodeError(f"input: {s!r}") from e

    def load(self, fp: IO[str]):
        try:
            return self.json.load(fp)
        except ValueError as e:
            raise JSONDecodeError from e

    def dump(
        self,
        data: Any,
        fp: IO[str],
        indent=0,
        sort_keys=False,
        quote_keys=False,
        **kwargs,
    ):
        try:
            self.json.dump(
                data,
                fp,
                indent=indent,
                sort_keys=sort_keys,
                quote_keys=quote_keys,
                ensure_ascii=kwargs.get("ensure_ascii", False),
            )
        except ValueError as e:
            raise JSONDecodeError from e

    def dumps(self, obj: Any, indent=0, sort_keys=False, **kwargs):
        try:
            return self.dumps(
                obj,
                indent=indent,
                sort_keys=sort_keys,
                ensure_ascii=kwargs.get("ensure_ascii", False),
            )
        except ValueError as e:
            raise JSONDecodeError(e)
