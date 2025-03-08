from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)
from demisto_sdk.commands.content_graph.strict_objects.list import StrictList


class ListParser(JSONContentItemParser, content_type=ContentType.LIST):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        pack_supported_modules: List[str],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(
            path, pack_marketplaces, pack_supported_modules, git_sha=git_sha
        )
        self.type = self.json_data.get("type")

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return set(MarketplaceVersions)

    @property
    def is_unified(self) -> bool:
        return bool((data := self.json_data.get("data")) and data != "-")

    @property
    def strict_object(self):
        return StrictList
