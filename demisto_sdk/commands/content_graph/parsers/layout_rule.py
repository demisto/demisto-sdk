from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)


class LayoutRuleParser(JSONContentItemParser, content_type=ContentType.LAYOUT_RULE):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)

        self.connect_to_dependencies()

    @property
    def object_id(self) -> Optional[str]:
        return self.json_data.get("rule_id")

    @property
    def name(self) -> Optional[str]:
        return self.json_data.get("rule_name")

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2}

    def connect_to_dependencies(self) -> None:
        """Collects t he playbook used in the trigger as a mandatory dependency."""
        if layout := self.json_data.get("layout_id"):
            self.add_dependency_by_id(layout, ContentType.LAYOUT)
