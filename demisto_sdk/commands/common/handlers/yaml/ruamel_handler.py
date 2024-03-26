from io import StringIO

from ruamel.yaml import YAML  # noqa:TID251 - this is the handler

from demisto_sdk.commands.common.handlers.handlers_utils import order_dict
from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler


class RUAMEL_Handler(XSOAR_Handler):
    """
    XSOAR wrapper to ruamel.yaml.
    Use only this wrapper for yaml handling.
    """

    def __init__(
        self,
        typ="rt",
        preserve_quotes=True,
        allow_duplicate_keys=False,
        width=5000,
        ensure_ascii=False,
        indent=0,
    ):
        """
        typ: 'rt'/None -> RoundTripLoader/RoundTripDumper,  (default, preserves order, comments and formatting. slower then the rest))
             'safe'    -> SafeLoader/SafeDumper,
             'unsafe'  -> normal/unsafe Loader/Dumper
             'base'    -> baseloader

        """
        self._typ = typ
        self._preserve_quotes = preserve_quotes
        self._allow_duplicate_keys = allow_duplicate_keys
        self._width = width
        self._allow_unicode = not ensure_ascii
        self.indent = indent

    @property
    def yaml(self) -> YAML:
        """Creating an instance of ruamel for each command. Best practice by ruamel"""
        yaml = YAML(typ=self._typ)
        yaml.allow_duplicate_keys = self._allow_duplicate_keys
        yaml.preserve_quotes = self._preserve_quotes
        yaml.width = self._width
        yaml.allow_unicode = self._allow_unicode
        return yaml

    def load(self, stream):
        return self.yaml.load(stream)

    def dump(self, data, stream, indent=None, sort_keys=False, **kwargs):
        if sort_keys:
            data = order_dict(data)
        yaml = self.yaml
        indent = indent if indent is not None else self.indent
        if indent:
            yaml.indent(sequence=indent)
        yaml.dump(data, stream)

    def dumps(self, data, indent=None, sort_keys=False, **kwargs):
        """

        This function is not recommended and not efficient!
        https://yaml.readthedocs.io/en/latest/example.html#output-of-dump-as-a-string

        Used for BC to PyYAML to support dumping to string.
        to print a YAML, it is better to use `yaml.dump(data, sys.stdout)`
        """
        string_stream = StringIO()
        self.dump(
            data,
            string_stream,
            sort_keys=sort_keys,
            indent=indent if indent is not None else self.indent,
        )
        output_str = string_stream.getvalue()
        string_stream.close()
        return output_str
