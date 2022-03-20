from typing import TextIO

import ujson

from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler


class UJSON_Handler(XSOAR_Handler):
    """
    XSOAR wrapper to orjso
    Use only this wrapper for yaml handling.
    """

    def load(self, stream: TextIO):
        return ujson.load(stream)

    def dump(self, data, stream: TextIO, sort_keys=False, indent=None):
        ujson.dump(data, stream, sort_keys=sort_keys, indent=indent)

    def dumps(self, data, sort_keys=False, indent=None):
        return ujson.dumps(
            data,
            sort_keys=sort_keys,
            indent=indent
        )
