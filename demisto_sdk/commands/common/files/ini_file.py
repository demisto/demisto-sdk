from configparser import ConfigParser, MissingSectionHeaderError
from pathlib import Path
from typing import Dict, Optional, Set

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
)
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
            logger.debug(f"Got error when trying to parse INI file, error: {e}")
            return False

    def __read_as_config_parser(self, file_content: str) -> Optional[ConfigParser]:
        try:
            config_parser = ConfigParser(allow_no_value=True)
            config_parser.read_string(file_content)
            return config_parser
        except MissingSectionHeaderError:
            logger.error(f"Error when retrieving the content of {self.input_path}")
            return None

    def read_local_file(self) -> Optional[ConfigParser]:
        return self.__read_as_config_parser(super().read_local_file())

    def read_local_file_git(
        self, tag: str = DEMISTO_GIT_PRIMARY_BRANCH
    ) -> Optional[ConfigParser]:
        return self.__read_as_config_parser(super().read_local_file_git(tag))

    def read_origin_file_git(
        self, branch: str = DEMISTO_GIT_PRIMARY_BRANCH
    ) -> Optional[ConfigParser]:
        return self.__read_as_config_parser(super().read_origin_file_git(branch=branch))

    def write(self, data: Dict) -> None:
        config = ConfigParser()
        for section, values in data.items():
            config[section] = values

        with self.output_path.open("w", encoding=self.default_encoding) as ini_file:
            config.write(ini_file)
