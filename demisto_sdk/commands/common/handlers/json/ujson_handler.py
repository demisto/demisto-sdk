from typing import IO, Any, AnyStr

import ujson

from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler


class JSONDecodeError(ValueError):
    pass


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
            return ujson.loads(s)
        except ValueError as e:
            raise JSONDecodeError(e)

    def load(self, fp: IO[str]):
        try:
            return ujson.load(fp)
        except ValueError as e:
            raise JSONDecodeError(e)

    def dump(self, obj: Any, fp: IO[str], indent=0, sort_keys=False):
        try:
            ujson.dump(
                obj,
                fp,
                indent=indent,
                sort_keys=sort_keys,
                escape_forward_slashes=False
            )
        except ValueError as e:
            raise JSONDecodeError(e)

    def dumps(self, obj: Any, indent=0, sort_keys=False):
        try:
            return ujson.dumps(
                obj,
                sort_keys=sort_keys,
                indent=indent,
                escape_forward_slashes=False
            )
        except ValueError as e:
            raise JSONDecodeError(e)
