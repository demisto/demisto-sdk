from abc import abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.docker_helper import get_python_version_from_dockerhub_api
from demisto_sdk.commands.common.docker_images_metadata import DockerImagesMetadata
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)
from demisto_sdk.commands.common.logger import logger


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
    @abstractmethod
    def type(self) -> str:
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

    @property
    def python_version(self) -> Optional[str]:
        """
        Get python version of scripts/integrations which are based on python images
        """
        if python_version := DockerImagesMetadata().python_version(self.docker_image):
            return python_version
        logger.debug(
            f'Could not get python version for {self.object_id=} from dockerfiles-info, will retrieve from dockerhub api'
        )

        if python_version := get_python_version_from_dockerhub_api(self.docker_image):
            return str(python_version)
        logger.debug(
            f'Could not get python version for {self.object_id=} using {self.docker_image=} from dockerhub api'
        )

        return None
