from typing import AnyStr, TextIO

import ujson

from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler


class JSONDecodeError(ValueError):
    pass


class UJSON_Handler(XSOAR_Handler):
    """
    XSOAR wrapper to UJSON
    Use only this wrapper for yaml handling.
    """
    JSONDecodeError = JSONDecodeError

    def __init__(self):
        self.json = ujson

    def loads(self, s: AnyStr):
        try:
            return ujson.loads(s)
        except ValueError as e:
            raise JSONDecodeError(e)

    def load(self, stream: TextIO):
        try:
            return ujson.load(stream)
        except ValueError as e:
            raise JSONDecodeError(e)

    def dump(self, data, stream: TextIO, sort_keys=False, indent=0):
        try:
            ujson.dump(data, stream, sort_keys=sort_keys, indent=indent)
        except ValueError as e:
            raise JSONDecodeError(e)

    def dumps(self, data, sort_keys=False, indent=0):
        try:
            return ujson.dumps(
                data,
                sort_keys=sort_keys,
                indent=indent
            )
        except ValueError as e:
            raise JSONDecodeError(e)
