from abc import abstractmethod
from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import \
    YAMLContentItemParser
from demisto_sdk.commands.unify.integration_script_unifier import \
    IntegrationScriptUnifier


class IntegrationScriptParser(YAMLContentItemParser):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        self.is_unified = YAMLContentItemParser.is_unified_file(path)
        # IntegrationScriptUnifier must accept a directory path
        self.unifier = (
            None if self.is_unified else IntegrationScriptUnifier(path.as_posix())
        )
        # after super().__init__(), self.path will be the integration's yml path
        super().__init__(path, pack_marketplaces)

    @property
    def object_id(self) -> Optional[str]:
        return self.yml_data.get("commonfields", {}).get("id")

    @abstractmethod
    def get_code(self) -> Optional[str]:
        pass
