"""
Imports below are required to identify all the sub-classes of File object
"""
from demisto_sdk.commands.common.files.binary_file import BinaryFile  # noqa: F401
from demisto_sdk.commands.common.files.file import File  # noqa: F401
from demisto_sdk.commands.common.files.handler_file import HandlerFile  # noqa: F401
from demisto_sdk.commands.common.files.ini_file import IniFile  # noqa: F401
from demisto_sdk.commands.common.files.json_file import JsonFile  # noqa: F401
from demisto_sdk.commands.common.files.text_file import TextFile  # noqa: F401
from demisto_sdk.commands.common.files.yml_file import YmlFile  # noqa: F401
