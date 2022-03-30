"""
This is for source of truth of handlers
"""

from .json.ujson_handler import UJSON_Handler as JSON_Handler  # noqa: F401
from .yaml.ruamel_handler import RUAMEL_Handler as YAML_Handler  # noqa: F401
