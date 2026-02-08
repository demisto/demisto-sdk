from functools import cached_property
from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import (
    DEFAULT_AGENTIX_ITEM_FROM_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import get_value
from demisto_sdk.commands.content_graph.parsers.content_item import (
    NotAContentItemException,
)
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)


class AgentixBaseParser(YAMLContentItemParser):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        pack_supported_modules,
        git_sha: Optional[str] = None,
    ) -> None:
        self.is_unified = YAMLContentItemParser.is_unified_file(path)
        super().__init__(
            path, pack_marketplaces, pack_supported_modules, git_sha=git_sha
        )
        self.tags: List[str] = self.yml_data.get("tags", [])
        self.category: Optional[str] = self.yml_data.get("category", None)
        self.disabled: Optional[bool] = self.yml_data.get("disabled", False)
        self.internal: bool = self.yml_data.get("internal", False)

    def _is_test_file(self, path: Path) -> bool:
        """Check if a file is a test file based on its name pattern.

        Args:
            path (Path): The file path to check.

        Returns:
            bool: True if the file matches *_test.yaml or *_test.yml pattern.
        """
        stem = path.stem  # filename without extension
        return stem.endswith("_test")

    def get_path_with_suffix(self, suffix: str) -> Path:
        """Override to support both .yml and .yaml extensions for Agentix items,
        and to skip test files (*_test.yaml, *_test.yml).

        Args:
            suffix (str): The suffix of the content item (typically ".yml").

        Returns:
            Path: The path to the YAML file with either .yml or .yaml extension.

        Raises:
            NotAContentItemException: If no valid content file is found.
        """
        if not self.path.is_dir():
            # For non-directory paths, check if it's a test file
            if self._is_test_file(self.path):
                raise NotAContentItemException(f"Skipping test file: {self.path}")
            if not self.path.exists() or self.path.suffix not in (
                suffix,
                ".yml",
                ".yaml",
            ):
                raise NotAContentItemException
            return self.path

        # For directories, find all YAML files and filter out test files
        yaml_extensions = [".yml", ".yaml"]
        paths = [
            p
            for p in self.path.iterdir()
            if p.suffix in yaml_extensions and not self._is_test_file(p)
        ]

        if not paths:
            raise NotAContentItemException(f"No valid YAML files found in {self.path}")

        if len(paths) == 1:
            return paths[0]

        # Prefer the file that matches the directory name
        for path in paths:
            if path.stem == self.path.name:
                return path

        # Fall back to the first non-test file
        return paths[0]

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "object_id": "commonfields.id",
                "version": "commonfields.version",
            }
        )
        return super().field_mapping

    @property
    def display_name(self) -> Optional[str]:
        return get_value(self.yml_data, self.field_mapping.get("display", ""))

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.PLATFORM}

    @property
    def name(self) -> Optional[str]:
        return get_value(self.yml_data, self.field_mapping.get("name", ""))

    @property
    def fromversion(self) -> str:
        return str(
            get_value(
                self.yml_data,
                self.field_mapping.get("fromversion", ""),
                DEFAULT_AGENTIX_ITEM_FROM_VERSION,
            )
        )
