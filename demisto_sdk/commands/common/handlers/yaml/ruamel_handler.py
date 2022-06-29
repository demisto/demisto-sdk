from io import StringIO

from ruamel.yaml import YAML

from demisto_sdk.commands.common.handlers.handlers_utils import order_dict
from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler


class RUAMEL_Handler(XSOAR_Handler):
    """
    XSOAR wrapper to ruamel.yaml.
    Use only this wrapper for yaml handling.
    """

    def __init__(self, preserve_quotes=True, allow_duplicate_keys=False, width=5000):
        self._preserve_quotes = preserve_quotes
        self._allow_duplicate_keys = allow_duplicate_keys
        self._width = width

    @property
    def yaml(self) -> YAML:
        """Creating an instance of ruamel for each command. Best practice by ruamel"""
        yaml = YAML()
        yaml.allow_duplicate_keys = self._allow_duplicate_keys
        yaml.preserve_quotes = self._preserve_quotes
        yaml.width = self._width
        return yaml

    def load(self, stream):
        return self.yaml.load(stream)

    def dump(self, data, stream, indent=0, sort_keys=False, **kwargs):
        if sort_keys:
            data = order_dict(data)
        yaml = self.yaml
        if indent:
            yaml.indent(sequence=indent)
        yaml.dump(data, stream)

    def dumps(self, data, indent=0, sort_keys=False, **kwargs):
        """

        This function is not recommended and not efficient!
        https://yaml.readthedocs.io/en/latest/example.html#output-of-dump-as-a-string

        Used for BC to PyYAML to support dumping to string.
        to print a YAML, it is better to use `yaml.dump(data, sys.stdout)`
        """
        string_stream = StringIO()
        self.dump(data, string_stream, sort_keys=sort_keys, indent=indent)
        output_str = string_stream.getvalue()
        string_stream.close()
        return output_str
