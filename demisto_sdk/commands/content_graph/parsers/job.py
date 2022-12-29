from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)


class JobParser(JSONContentItemParser, content_type=ContentType.JOB):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)

        self.connect_to_dependencies()

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.XSOAR}

    @property
    def description(self) -> Optional[str]:
        return self.json_data.get("details")

    def connect_to_dependencies(self) -> None:
        if playbook := self.json_data.get("selectedFeeds"):
            raise Exception(
                "When supported, need to make sure selectedFeeds is a list of integrations "
                "on server side, because currently it's a list of instances."
            )
        if playbook := self.json_data.get("playbookId"):
            self.add_dependency_by_id(playbook, ContentType.PLAYBOOK)
