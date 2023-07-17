from abc import abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)


class IntegrationScriptParser(YAMLContentItemParser):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        self.is_unified = YAMLContentItemParser.is_unified_file(path)
        super().__init__(path, pack_marketplaces)
        self.script_info: Dict[str, Any] = self.yml_data.get("script", {})
        self.connect_to_api_modules()

    @property
    def object_id(self) -> Optional[str]:
        return self.yml_data.get("commonfields", {}).get("id")

    @property
    @abstractmethod
    def docker_image(self) -> str:
        ...

    @property
    @abstractmethod
    def code(self) -> Optional[str]:
        pass

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.XPANSE,
        }

    def connect_to_api_modules(self) -> None:
        """Creates IMPORTS relationships with the API modules used in the integration."""
        code = self.code
        if not code:
            raise ValueError("Integration code is not available")
        api_modules = IntegrationScriptUnifier.check_api_module_imports(code).values()
        for api_module in api_modules:
            self.add_relationship(
                RelationshipType.IMPORTS, api_module, ContentType.SCRIPT
            )
