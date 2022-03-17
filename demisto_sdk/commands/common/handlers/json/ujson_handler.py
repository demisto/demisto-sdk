import ujson

from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler


class UJSON_Handler(XSOAR_Handler):
    """
    XSOAR wrapper to ujson
    Use only this wrapper for yaml handling.
    """

    def load(self, stream):
        return ujson.load(stream)

    def dump(self, data, stream, indent=None, sort_keys=False):
        ujson.dump(data, stream, indent=indent, sort_keys=sort_keys)

    def dumps(self, data, sort_keys=False, indent=None):
        return ujson.dumps(data, sort_keys=sort_keys, indent=indent)
