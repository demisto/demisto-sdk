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


class XSIAMReportParser(JSONContentItemParser, content_type=ContentType.XSIAM_REPORT):
    XSIAMREPORTPARSER_MAPPING = {
        "name": "report_name",
        "description": "report_description",
        "object_id": "global_id",
        "fromversion": "fromVersion",
        "toVersion": "toVersion",
    }

    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)
        self.add_to_mapping(self.XSIAMREPORTPARSER_MAPPING)
        self.json_data: Dict[str, Any] = self.json_data.get("templates_data", [{}])[0]

    @property
    def name(self) -> Optional[str]:
        return get(self.json_data, self.MAPPING.get("name", ""))

    @property
    def description(self) -> Optional[str]:
        return get(self.json_data, self.MAPPING.get("description", ""))

    @property
    def object_id(self) -> Optional[str]:
        return get(self.json_data, self.MAPPING.get("object_id", ""))

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2}

    @property
    def fromversion(self) -> str:
        return get(
            self.json_data,
            self.MAPPING.get("fromversion", ""),
            DEFAULT_CONTENT_ITEM_FROM_VERSION,
        )

    @property
    def toversion(self) -> str:
        return get(
            self.json_data,
            self.MAPPING.get("toversion", ""),
            DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
