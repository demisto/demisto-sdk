from pathlib import Path
from typing import List, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)


class CorrelationRuleParser(
    YAMLContentItemParser, content_type=ContentType.CORRELATION_RULE
):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)

    @property
    def object_id(self) -> str:
        return self.yml_data["global_rule_id"]

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2}

    @staticmethod
    def match(_dict: dict, path: str) -> bool:
        return YAMLContentItemParser.match(_dict, path) and (
            "global_rule_id" in _dict
            or (isinstance(_dict, list) and _dict and "global_rule_id" in _dict[0])
        )
