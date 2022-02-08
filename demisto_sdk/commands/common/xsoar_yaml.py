from io import StringIO

from ruamel.yaml import YAML


class XSOAR_YAML:
    """
    XSOAR wrapper to ruamel.yaml.
    Use only this wrapper for yaml handling.
    """

    def __init__(self, typ=None, preserve_quotes=True, allow_duplicate_keys=False, width=5000):
        self._ryaml = YAML(typ=typ)
        self._ryaml.preserve_quotes = preserve_quotes
        self._ryaml.allow_duplicate_keys = allow_duplicate_keys
        self._ryaml.width = width

    @staticmethod
    def _order_dict(data):
        """
        Alternative for PyYAML `sort_keys` argument
        """
        return {k: XSOAR_YAML._order_dict(v) if isinstance(v, dict) else v
                for k, v in sorted(data.items())}

    def load(self, stream):
        return self._ryaml.load(stream)

    def dump(self, data, stream, sort_keys=False):
        if sort_keys:
            data = XSOAR_YAML._order_dict(data)
        self._ryaml.dump(data, stream)

    def dumps(self, data, sort_keys=False):
        """

        This function is not recommended and not efficient!
        https://yaml.readthedocs.io/en/latest/example.html#output-of-dump-as-a-string

        Used for BC to PyYAML to support dumping to string.
        to print a YAML, it is better to use `xsoar_yaml.dump(data, sys.stdout)`
        """
        if sort_keys:
            data = XSOAR_YAML._order_dict(data)
        string_stream = StringIO()
        self._ryaml.dump(data, string_stream)
        output_str = string_stream.getvalue()
        string_stream.close()
        return output_str
