from functools import cached_property
from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_value
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

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "object_id": "commonfields.id",
                "version": "commonfields.version",
                "name": "commonfields.id",
            }
        )
        return super().field_mapping

    @property
    def display_name(self) -> Optional[str]:
        return get_value(self.yml_data, self.field_mapping.get("display", ""))

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return set(MarketplaceVersions)

    @property
    def name(self) -> Optional[str]:
        return get_value(self.yml_data, self.field_mapping.get("name", ""))
