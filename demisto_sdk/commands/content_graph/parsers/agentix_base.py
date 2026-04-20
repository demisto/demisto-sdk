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

    def get_path_with_suffix(self, suffix: str) -> Path:
        """Override to support both .yml and .yaml extensions for Agentix items.

        Args:
            suffix (str): The suffix of the content item (typically ".yml").

        Returns:
            Path: The path to the YAML file with either .yml or .yaml extension.
        """
        # Try the requested suffix first
        try:
            return super().get_path_with_suffix(suffix)
        except NotAContentItemException:
            # If .yml was requested but not found, try .yaml
            if suffix == ".yml":
                return super().get_path_with_suffix(".yaml")
            # If .yaml was requested but not found, try .yml
            elif suffix == ".yaml":
                return super().get_path_with_suffix(".yml")
            raise

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
