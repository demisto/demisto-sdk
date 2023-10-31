from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import get
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)


class XSIAMDashboardParser(
    JSONContentItemParser, content_type=ContentType.XSIAM_DASHBOARD
):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(path, pack_marketplaces, git_sha=git_sha)
        self.json_data: Dict[str, Any] = self.json_data.get("dashboards_data", [{}])[0]

    @cached_property
    def mapping(self):
        return super().mapping.update({
            "object_id": "global_id",
            "fromversion": "fromVersion",
            "toVersion": "toVersion",
        })

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2}

    @property
    def object_id(self) -> Optional[str]:
        return get(self.json_data, self.mapping.get("object_id", ""))

    @property
    def fromversion(self) -> str:
        return get(
            self.json_data,
            self.mapping.get("fromversion", ""),
            DEFAULT_CONTENT_ITEM_FROM_VERSION,
        )

    @property
    def toversion(self) -> str:
        return get(
            self.json_data,
            self.mapping.get("toversion", ""),
            DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
