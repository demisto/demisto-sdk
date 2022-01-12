from ruamel.yaml import YAML


class XSOAR_YAML:
    def __init__(self, preserve_quotes=True, allow_duplicate_keys=True, default_flow_style=None, width=None, typ=None):
        self.xsoar_yaml = YAML()
        self.xsoar_yaml.preserve_quotes = preserve_quotes
        self.xsoar_yaml.allow_duplicate_keys = allow_duplicate_keys
        self.xsoar_yaml.default_flow_style = default_flow_style
        self.xsoar_yaml.width = width
        self.xsoar_yaml.typ = typ

    def load(self, stream):
        return self.xsoar_yaml.load(stream)

    def dump(self, data, stream, **kwargs):
        return self.xsoar_yaml.dump(data, stream, **kwargs)