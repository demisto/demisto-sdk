from abc import abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.docker.docker_image import DockerImage
from demisto_sdk.commands.common.tools import get_value
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)


class IntegrationScriptParser(YAMLContentItemParser):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        git_sha: Optional[str] = None,
    ) -> None:
        self.is_unified = YAMLContentItemParser.is_unified_file(path)
        super().__init__(path, pack_marketplaces, git_sha=git_sha)
        self.script_info: Dict[str, Any] = self.yml_data.get("script", {})
        self.connect_to_api_modules()

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {"object_id": "commonfields.id", "version": "commonfields.version"}
        )
        return super().field_mapping

    @cached_property
    def docker_image(self) -> DockerImage:
        docker_image = (
            get_value(self.yml_data, self.field_mapping.get("docker_image", ""), "")
            or ""
        )
        return DockerImage(docker_image)

    @property
    def alt_docker_images(self) -> List[str]:
        return get_value(
            self.yml_data, self.field_mapping.get("alt_docker_images", []), []
        )

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
            MarketplaceVersions.XSOAR_SAAS,
            MarketplaceVersions.XSOAR_ON_PREM,
        }

    def connect_to_api_modules(self) -> None:
        """Creates IMPORTS relationships with the API modules used in the integration."""
        code = self.code
        if not code:
            raise ValueError(
                f"Could not get integration code from {self.object_id} integration lying in folder {self.path.parent}"
            )
        api_modules = IntegrationScriptUnifier.check_api_module_imports(code).values()
        for api_module in api_modules:
            self.add_relationship(
                RelationshipType.IMPORTS, api_module, ContentType.SCRIPT
            )

    @property
    def type(self):
        return get_value(self.yml_data, self.field_mapping.get("type", ""))

    @property
    def subtype(self):
        subtype = get_value(self.yml_data, self.field_mapping.get("subtype", ""))
        if not subtype and self.type == "python":
            subtype = "python2"
        return subtype
