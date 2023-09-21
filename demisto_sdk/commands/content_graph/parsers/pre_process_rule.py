from typing import Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)


class PreProcessRuleParser(
    JSONContentItemParser, content_type=ContentType.PREPROCESS_RULE
):
    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.XSOAR_SAAS,
            MarketplaceVersions.XSOAR_ON_PREM,
        }

    @staticmethod
    def match(_dict: dict, path: str) -> bool:
        return JSONContentItemParser.match(_dict, path) and (
            "scriptName" in _dict
            and "existingEventsFilters" in _dict
            and "readyExistingEventsFilters" in _dict
            and "newEventFilters" in _dict
            and "readyNewEventFilters" in _dict
        )
