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

    def dump(self, data: Any, fp: IO[str], **kwargs):
        try:
            ujson.dump(
                data,
                fp,
                indent=kwargs.get('indent', 0),
                sort_keys=kwargs.get('sort_keys', False),
                escape_forward_slashes=kwargs.get('escape_forward_slashes', False),
                encode_html_chars=kwargs.get('encode_html_chars', False),
                ensure_ascii=kwargs.get('ensure_ascii', True)
            )
        except ValueError as e:
            raise JSONDecodeError(e)

    def dumps(self, obj: Any, **kwargs):
        try:
            return ujson.dumps(
                obj,
                indent=kwargs.get('indent', 0),
                sort_keys=kwargs.get('sort_keys', False),
                escape_forward_slashes=kwargs.get('escape_forward_slashes', False)
            )
        except ValueError as e:
            raise JSONDecodeError(e)
