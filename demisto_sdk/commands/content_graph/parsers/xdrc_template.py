from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)


class XDRCTemplateParser(JSONContentItemParser, content_type=ContentType.XDRC_TEMPLATE):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)
        self.content_global_id = self.json_data.get("content_global_id")
        self.os_type = self.json_data.get("os_type")
        self.profile_type = self.json_data.get("profile_type")

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2}

    @property
    def object_id(self) -> Optional[str]:
        return self.json_data.get("content_global_id")
