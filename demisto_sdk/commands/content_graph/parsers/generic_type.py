from pathlib import Path
from typing import List, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)


class GenericTypeParser(JSONContentItemParser, content_type=ContentType.GENERIC_TYPE):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)
        self.definition_id = self.json_data.get("definitionId")

        self.connect_to_dependencies()

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.XSOAR}

    def connect_to_dependencies(self) -> None:
        """Collects the layouts used in the generic type as mandatory dependencies."""
        if layout := self.json_data.get("layout"):
            self.add_dependency_by_id(layout, ContentType.LAYOUT)
