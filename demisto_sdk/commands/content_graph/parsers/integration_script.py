from abc import abstractmethod
from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)


class IntegrationScriptParser(YAMLContentItemParser):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        self.is_unified = YAMLContentItemParser.is_unified_file(path)
        super().__init__(path, pack_marketplaces)

    @property
    def object_id(self) -> Optional[str]:
        return self.yml_data.get("commonfields", {}).get("id")

    @abstractmethod
    def get_code(self) -> Optional[str]:
        pass

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.XPANSE,
        }
