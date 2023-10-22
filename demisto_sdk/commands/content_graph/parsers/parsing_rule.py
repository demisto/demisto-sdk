from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)


class ParsingRuleParser(YAMLContentItemParser, content_type=ContentType.PARSING_RULE):
    PARSINGRULEPARSER_MAPPING = {
        "object_id": "id"
    }
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)
        self.add_to_mapping(self.PARSINGRULEPARSER_MAPPING)

    @property
    def object_id(self) -> Optional[str]:
        return get(self.yml_data, self.MAPPING.get("object_id", ""))

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2}
