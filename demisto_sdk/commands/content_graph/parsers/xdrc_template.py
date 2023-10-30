from functools import cached_property
from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)


class XDRCTemplateParser(JSONContentItemParser, content_type=ContentType.XDRC_TEMPLATE):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(path, pack_marketplaces, git_sha=git_sha)
        self.content_global_id = self.json_data.get("content_global_id")
        self.os_type = self.json_data.get("os_type")
        self.profile_type = self.json_data.get("profile_type")

    @cached_property
    def mapping(self):
        return super().mapping | {"object_id": "content_global_id"}

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2}

    @property
    def object_id(self) -> Optional[str]:
        return get(self.json_data, self.mapping.get("object_id", ""))
