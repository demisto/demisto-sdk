from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions, MODELING_RULES_DIR
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)


class ModelingRuleParser(YAMLContentItemParser, content_type=ContentType.MODELING_RULE):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)

    @property
    def object_id(self) -> Optional[str]:
        return self.yml_data.get("id")

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.MarketplaceV2}

    @staticmethod
    def match(_dict: dict, path: str) -> bool:
        return (
            YAMLContentItemParser.match(_dict, path)
            and MODELING_RULES_DIR in Path(path).parts
            and "rules" in _dict)
