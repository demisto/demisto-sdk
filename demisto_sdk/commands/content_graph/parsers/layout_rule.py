from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)


class LayoutRuleParser(JSONContentItemParser, content_type=ContentType.LAYOUT_RULE):

    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions], git_sha: Optional[str] = None
    ) -> None:
        super().__init__(path, pack_marketplaces, git_sha=git_sha)
        self.connect_to_dependencies()
    
    @property
    def mapping(self):
        return super().mapping | {
        "object_id": "rule_id",
        "name": "rule_name",
        "layout_id": "layout_id",
    }

    @property
    def object_id(self) -> Optional[str]:
        return get(self.json_data, self.mapping.get("object_id", ""))

    @property
    def name(self) -> Optional[str]:
        return get(self.json_data, self.mapping.get("name", ""))

    @property
    def layout_id(self) -> Optional[str]:
        return get(self.json_data, self.mapping.get("layout_id", ""))

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.XSOAR_SAAS,
            MarketplaceVersions.XSOAR_ON_PREM,
        }

    def connect_to_dependencies(self) -> None:
        """Collects t he playbook used in the trigger as a mandatory dependency."""
        if layout := self.json_data.get("layout_id"):
            self.add_dependency_by_id(layout, ContentType.LAYOUT)
