from io import StringIO

from ruamel.yaml import YAML


class XSOAR_YAML:
    def __init__(self, preserve_quotes=True, allow_duplicate_keys=True, default_flow_style=None, width=None, typ=None):
        self.ryaml = YAML()
        self.ryaml.preserve_quotes = preserve_quotes
        self.ryaml.allow_duplicate_keys = allow_duplicate_keys
        self.ryaml.default_flow_style = default_flow_style
        self.ryaml.width = width
        self.ryaml.typ = typ

    @staticmethod
    def _order_dict(data):
        return {k: XSOAR_YAML._order_dict(v) if isinstance(v, dict) else v
                for k, v in sorted(data.items())}

    def load(self, stream):
        return self.ryaml.load(stream)

    def dump(self, data, stream=None, sort_keys=False, **kwargs):
        if stream is None:
            string_stream = StringIO()
            self.ryaml.dump(data, string_stream)
            output_str = string_stream.getvalue()
            string_stream.close()
            return output_str
        if sort_keys:
            data = XSOAR_YAML._order_dict(data)
        return self.ryaml.dump(data, stream, **kwargs)
