from configparser import ConfigParser
from pathlib import Path
from typing import Any, Optional, Set

from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.logger import logger


class IniFile(TextFile):
    @classmethod
    def known_files(cls) -> Set[str]:
        return {".pack-ignore"}

    @classmethod
    def known_extensions(cls) -> Set[str]:
        return {".ini"}

    @classmethod
    def is_class_type(cls, path: Path) -> bool:
        if super().is_class_type(path):
            return True

        try:
            parser = ConfigParser()
            parser.read(path)
            return bool(parser.sections())
        except Exception as e:
            logger.debug(f"Got error when trying to parse INI file\nerror:{e}")
            return False

    def load(self, file_content: str) -> Optional[ConfigParser]:
        config_parser = ConfigParser(allow_no_value=True)
        config_parser.read_string(file_content)
        return config_parser

    def _write(self, data: Any, path: Path, encoding: Optional[str] = None) -> None:
        """

        Args:
            data:
            encoding:

        Returns:

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
        config = ConfigParser()
        for section, values in data.items():
            config[section] = values

        with path.open(
            "w", encoding=encoding or self.default_encoding
        ) as ini_file:
            config.write(ini_file)
