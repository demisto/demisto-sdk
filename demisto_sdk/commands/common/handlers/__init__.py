"""
This is for source of truth of handlers
"""

from .json.json5_handler import JSON5_Handler
from .json.ujson_handler import UJSON_Handler as JSON_Handler
from .xsoar_handler import XSOAR_Handler  # noqa: F401
from .yaml.ruamel_handler import RUAMEL_Handler as YAML_Handler

DEFAULT_JSON_HANDLER = (
    JSON_Handler()
)  # use this when additional arguments are not necessary
DEFAULT_YAML_HANDLER = (
    YAML_Handler()
)  # use this when additional arguments are not necessary
DEFAULT_JSON5_HANDLER = JSON5_Handler()
