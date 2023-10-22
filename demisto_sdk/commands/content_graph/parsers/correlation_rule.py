from pathlib import Path
from typing import List, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)


class CorrelationRuleParser(
    YAMLContentItemParser, content_type=ContentType.CORRELATION_RULE
):
    CORRELATIONRULEPARSER_MAPPING = {"object_id": "global_rule_id"}
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)
        self.add_to_mapping(self.CORRELATIONRULEPARSER_MAPPING)

    @property
    def object_id(self) -> str:
        return get(self.yml_data, self.MAPPING.get("object_id", ""))

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2}
