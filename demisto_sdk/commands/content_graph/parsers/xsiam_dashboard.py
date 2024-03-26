from functools import cached_property
from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import (
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
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(path, pack_marketplaces, git_sha=git_sha)

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "object_id": [
                    "dashboards_data[0].global_id",
                    "dashboards_data[0].id",
                ],
                "fromversion": "fromVersion",
                "toversion": "toVersion",
                "name": "dashboards_data[0].name",
                "deprecated": "dashboards_data[0].deprecated",
                "description": "dashboards_data[0].description",
            }
        )
        return super().field_mapping

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2}
