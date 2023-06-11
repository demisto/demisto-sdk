from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)


class XSIAMDashboardParser(
    JSONContentItemParser, content_type=ContentType.XSIAM_DASHBOARD
):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)
        self.json_data: Dict[str, Any] = self.json_data.get("dashboards_data", [{}])[0]

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2}

    @property
    def object_id(self) -> Optional[str]:
        return self.json_data.get("global_id")

    @property
    def fromversion(self) -> str:
        return (
            self.original_json_data.get("fromVersion")
            or DEFAULT_CONTENT_ITEM_FROM_VERSION
        )

    @property
    def toversion(self) -> str:
        return (
            self.original_json_data.get("toVersion") or DEFAULT_CONTENT_ITEM_TO_VERSION
        )
