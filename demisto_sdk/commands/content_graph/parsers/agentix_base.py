from datetime import datetime
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
        self.is_enabled: bool = self.yml_data.get("isEnabled", False)
        self.pack_id1: str = self.yml_data.get("packID", '')
        self.pack_name1: str = self.yml_data.get("packName", '')
        self.tags: List[str] = self.yml_data.get("tags", [])
        self.is_system: bool = self.yml_data.get("isSystem", True)
        self.is_locked: bool = self.yml_data.get("isLocked", True)
        self.is_detached: bool = self.yml_data.get("isDetached", False)
        self.modified: Optional[datetime] = self.yml_data.get("modified", None)
        self.modified_by: Optional[str] = self.yml_data.get("modifiedBy", None)
        self.category: Optional[str] = self.yml_data.get("category", None)
        self._id: str = self.yml_data.get("id", '')

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "object_id": "id",
            }
        )
        return super().field_mapping

    @property
    def display_name(self) -> Optional[str]:
        return self.yml_data.get("display", [])

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return set(MarketplaceVersions)
