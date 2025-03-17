from typing import Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.layout import (
    LayoutParser,
)
from demisto_sdk.commands.content_graph.strict_objects.case_layout import (
    StrictCaseLayout,
)


class CaseLayoutParser(LayoutParser, content_type=ContentType.CASE_LAYOUT):
    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2, MarketplaceVersions.PLATFORM}

    @property
    def strict_object(self):
        return StrictCaseLayout
