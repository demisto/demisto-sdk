from typing import IO, Optional

import orjson  # noqa: TID251 - this is the handler

from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler


class OrJSON_Handler(XSOAR_Handler):
    """
    XSOAR wrapper to orjson
    Use only this wrapper for json handling.
    """

    def load(self, fp: IO[str]):
        data = fp.read()
        return orjson.loads(data)

    def dump(self, data, fp: IO[str], indent=None, sort_keys=False, **kwargs):
        data = self.dumps(data, sort_keys=sort_keys, indent=indent, **kwargs)
        fp.write(data)

    def dumps(self, data, indent=None, sort_keys=False, **kwargs):
        return orjson.dumps(
            data,
            option=self._indent_level(indent) | self._sort_keys(sort_keys),
            **kwargs,  # if JSON_Handler will be replaced to OrJson, make sure to extract kwargs to prevent from
            # unwanted variables to be passed. See ujson dump implementation for example.
        )

    @staticmethod
    def _indent_level(indent: Optional[int] = None):
        if indent == 4:
            return orjson.OPT_INDENT_2
        return None

    @staticmethod
    def _sort_keys(sort_keys: bool):
        return orjson.OPT_SORT_KEYS if sort_keys else None
