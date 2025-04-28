from datetime import datetime
from abc import abstractmethod
from pathlib import Path
from typing import List, Optional, Set
from demisto_sdk.commands.common.constants import MarketplaceVersions

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
        self.is_enabled: bool = self.yml_data.get("isEnabled")
        self.pack_id: str = self.yml_data.get("packID")
        self.pack_name: str = self.yml_data.get("packName")
        self.tags: list[str] = self.yml_data.get("tags")
        self.is_system: bool = self.yml_data.get("isSystem")
        self.is_locked: bool = self.yml_data.get("isLocked")
        self.is_detached: bool = self.yml_data.get("isDetached")
        self.modified: Optional[datetime] = self.yml_data.get("modified", None)
        self.modified_by: Optional[str] = self.yml_data.get("modifiedBy", None)
        self.category: Optional[str] = self.yml_data.get("category", None)
        self._id: str = self.yml_data.get("id")
        self.display: str = self.yml_data.get("name")

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return set(MarketplaceVersions)
