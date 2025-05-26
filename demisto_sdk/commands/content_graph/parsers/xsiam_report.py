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
from demisto_sdk.commands.content_graph.strict_objects.xsiam_report import (
    StrictXSIAMReport,
)


class XSIAMReportParser(JSONContentItemParser, content_type=ContentType.XSIAM_REPORT):
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

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "name": "templates_data[0].report_name",
                "description": "templates_data[0].report_description",
                "object_id": "templates_data[0].global_id",
                "fromversion": "fromVersion",
                "toversion": "toVersion",
            }
        )
        return super().field_mapping

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2, MarketplaceVersions.PLATFORM}

    @property
    def strict_object(self):
        return StrictXSIAMReport
