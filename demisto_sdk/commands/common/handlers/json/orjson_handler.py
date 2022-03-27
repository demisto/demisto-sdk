from typing import Optional, TextIO

import orjson

from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler


class OrJSON_Handler(XSOAR_Handler):
    """
    XSOAR wrapper to orjson
    Use only this wrapper for json handling.
    """

    def load(self, stream: TextIO):
        data = stream.read()
        return orjson.loads(data)

    def dump(self, data, stream: TextIO, sort_keys=False, indent=None):
        data = self.dumps(data, sort_keys=sort_keys, indent=indent)
        stream.write(data)

    def dumps(self, data, sort_keys=False, indent=None):
        return orjson.dumps(
            data,
            option=self._indent_level(indent) | self._sort_keys(sort_keys))

    @staticmethod
    def _indent_level(indent: Optional[int] = None):
        if indent == 4:
            return orjson.OPT_INDENT_2
        return None

    @staticmethod
    def _sort_keys(sort_keys: bool):
        return orjson.OPT_SORT_KEYS if sort_keys else None
