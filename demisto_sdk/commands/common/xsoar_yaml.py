from io import StringIO

from ruamel.yaml import YAML


class XSOAR_YAML:
    def __init__(self, preserve_quotes=True, allow_duplicate_keys=True, width=None, typ=None):
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

    def dump(self, data, stream=None, sort_keys=False, **kwargs):
        if sort_keys:
            data = XSOAR_YAML._order_dict(data)
        if not stream:
            string_stream = StringIO()
            self._ryaml.dump(data, string_stream, **kwargs)
            output_str = string_stream.getvalue()
            string_stream.close()
            return output_str
        self._ryaml.dump(data, stream, **kwargs)
