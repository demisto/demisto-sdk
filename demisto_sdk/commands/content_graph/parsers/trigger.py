from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)


class TriggerParser(JSONContentItemParser, content_type=ContentType.TRIGGER):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)

        self.connect_to_dependencies()

    @property
    def object_id(self) -> Optional[str]:
        return self.json_data.get("trigger_id")

    @property
    def name(self) -> Optional[str]:
        return self.json_data.get("trigger_name")

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2}

    def connect_to_dependencies(self) -> None:
        """Collects the playbook used in the trigger as a mandatory dependency."""
        if playbook := self.json_data.get("playbook_id"):
            self.add_dependency_by_id(playbook, ContentType.PLAYBOOK)
