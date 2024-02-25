from configparser import ConfigParser
from pathlib import Path
from typing import Any

from demisto_sdk.commands.common.constants import PACKS_PACK_IGNORE_FILE_NAME
from demisto_sdk.commands.common.files.errors import FileLoadError
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
        file_content_as_text = super().load(file_content)
        try:
            config_parser.read_string(file_content_as_text)
        except Exception as error:
            raise FileLoadError(
                error, class_name=self.__class__.__name__, path=self.safe_path
            )

        return config_parser

    def _do_write(self, data: Any, path: Path, **kwargs):
        """
        Writes an INI file.

        Args:
            data: the data to write
            path: the output path

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

        with path.open("w", encoding=self.encoding) as ini_file:
            config.write(ini_file, space_around_delimiters=False)
