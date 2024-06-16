from typing import Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.layout import (
    LayoutParser,
)


class CaseLayoutParser(LayoutParser, content_type=ContentType.CASE_LAYOUT):
    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2}
