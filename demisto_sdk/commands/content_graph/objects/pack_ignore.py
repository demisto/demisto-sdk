import tempfile
from configparser import ConfigParser, MissingSectionHeaderError
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, List, Set

from demisto_sdk.commands.common.constants import PACKS_PACK_IGNORE_FILE_NAME
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_remote_file_from_api


class PackIgnore(dict):
    class Section(str, Enum):
        KNOWN_WORDS = "known_words"
        TESTS_REQUIRE_NETWORK = "tests_require_network"
        FILE = "file:"
        IGNORE = "ignore"

    def __init__(self, content: ConfigParser, path: Path, *args, **kwargs):
        self._content = content
        self._path = path
        super().__init__(*args, **kwargs)

    @classmethod
    @lru_cache
    def __load(cls, pack_ignore_path: Path) -> "PackIgnore":
        """
        Load the .pack-ignore file into a ConfigParser from a given path
        """
        if pack_ignore_path.exists():
            try:
                config = ConfigParser(allow_no_value=True)
                config.read(pack_ignore_path)
                return cls(content=config, path=pack_ignore_path)
            except MissingSectionHeaderError:
                logger.error(
                    f"Error when retrieving the content of .pack-ignore in path {pack_ignore_path}"
                )
                raise
        logger.warning(
            f"[red]Could not find .pack-ignore file at path {pack_ignore_path}[/red]"
        )
        raise FileNotFoundError(
            f"Could not find the .pack-ignore path at {pack_ignore_path}"
        )

    def __map_files_to_ignored_validations(self):
        for section in filter(
            lambda _section: _section.startswith(self.Section.FILE),
            self._content.sections(),
        ):
            self.add(
                section,
                self._content[section],
                lambda x: set(x[self.Section.IGNORE].strip().split(","))
                if self.Section.IGNORE in x
                else set(),
            )

    @classmethod
    def from_path(cls, path: Path) -> "PackIgnore":
        """
        init the PackIgnore from a local file path.

        Args:
            path (Path): path of the pack.
        """
        return cls.__load(CONTENT_PATH / path / PACKS_PACK_IGNORE_FILE_NAME)

    @classmethod
    @lru_cache
    def from_remote_path(cls, remote_path: str, tag: str = "master") -> "PackIgnore":
        """
        init the PackIgnore from a remote file path.

        Args:
            remote_path (path): remote file path.
            tag (str): the branch/commit to retrieve the file content.
        """
        pack_ignore_file_content: bytes = (
            get_remote_file_from_api(remote_path, tag=tag, return_content=True) or b""  # type: ignore[assignment]
        )

        with tempfile.NamedTemporaryFile(
            prefix=f'{remote_path.replace("/", "_")}:{tag}-'
        ) as pack_ignore_path:
            pack_ignore_path.write(pack_ignore_file_content)
            pack_ignore = cls.__load(Path(pack_ignore_path.name))

        pack_ignore.__map_files_to_ignored_validations()
        return pack_ignore

    def add(self, key: str, section: Any, cast_func: Callable = lambda x: x) -> None:
        self.__setitem__(key, cast_func(section))

    def get(
        self, key: str, default: Any = None, cast_func: Callable = lambda x: x
    ) -> Any:
        """
        Get a section from the .pack-ignore, in case key does not exist, will add it for caching purposes

        Args:
            key (str): the key to add.
            default (Any): in case any default value is needed
            cast_func (Callable): cast to any type when adding the key
        """
        if self._content.has_section(key):
            section = self._content[key]
            if not super().get(key):
                self.add(key, section, cast_func)
            return super().get(key)

        return default

    @property
    def path(self) -> Path:
        return self._path

    @property
    def known_words(self) -> Set[str]:
        """
        Returns a list of all the known words within the .pack-ignore
        """
        return self.get(
            self.Section.KNOWN_WORDS, default=set(), cast_func=lambda x: set(x)
        )

    @property
    def script_integration_ids_tests_require_docker_network(self) -> Set[str]:
        """
        Returns a list of all the scripts/integration IDs within a pack that requires docker network for unit-testing.
        """
        return self.get(
            self.Section.TESTS_REQUIRE_NETWORK,
            default=set(),
            cast_func=lambda x: set(x),
        )

    def get_ignored_validations_by_file_name(self, file_name: str) -> Set:
        """
        Get the ignored validations of a file within the .pack-ignore if exist

        Args:
            file_name (str): file name to retrieve its ignored validations
        """
        return self.get(
            f"{self.Section.FILE}{file_name}",
            default=set(),
            cast_func=lambda x: set(x[self.Section.IGNORE].strip().split(","))
            if self.Section.IGNORE in x
            else set(),
        )

    def get_ignored_validations_by_file_names(self, file_names: List[str]) -> Set[str]:
        """
        Get the ignored validations of a list of files within the .pack-ignore if exist

        Args:
            file_names (List[str]): file names to retrieve their ignored validations
        """
        ignored_validations: Set[str] = set()

        for file_name in file_names:
            ignored_validations.union(
                self.get_ignored_validations_by_file_name(file_name)
            )

        return ignored_validations
