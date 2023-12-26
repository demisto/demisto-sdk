from configparser import ConfigParser
from pathlib import Path
from typing import Any, Optional

from demisto_sdk.commands.common.constants import PACKS_PACK_IGNORE_FILE_NAME
from demisto_sdk.commands.common.files.text_file import TextFile


class IniFile(TextFile):
    @classmethod
    def is_model_type_by_path(cls, path: Path) -> bool:
        return (
            path.name.lower() == PACKS_PACK_IGNORE_FILE_NAME
            or path.suffix.lower() == ".ini"
        )

    def load(self, file_content: bytes) -> ConfigParser:
        config_parser = ConfigParser(allow_no_value=True)
        config_parser.read_string(super().load(file_content))
        return config_parser

    def _write(self, data: Any, path: Path, encoding: Optional[str] = None, **kwargs):
        """
        Writes an INI file.

        Args:
            data: the data to write
            encoding: whether any custom encoding is needed

        data example:
            data = {
                'file:APIVoid.yml': {
                    'ignore': 'BA124'
                },
                'known_words': {
                    'apivoid': None
                }
            }

        """
        config = ConfigParser(allow_no_value=True)
        for section, values in data.items():
            config[section] = values

        with path.open("w", encoding=encoding or self.default_encoding) as ini_file:
            config.write(ini_file, space_around_delimiters=False)
