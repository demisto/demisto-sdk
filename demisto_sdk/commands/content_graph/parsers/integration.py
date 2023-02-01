from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.parsers.integration_script import (
    IntegrationScriptParser,
)
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)


@dataclass
class CommandParser:
    name: str
    deprecated: bool
    description: str


class IntegrationParser(IntegrationScriptParser, content_type=ContentType.INTEGRATION):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)
        self.script_info: Dict[str, Any] = self.yml_data.get("script", {})
        self.category = self.yml_data["category"]
        self.docker_image = self.script_info.get("dockerimage", "")
        self.is_fetch = self.script_info.get("isfetch", False)
        self.is_fetch_events = self.script_info.get("isfetchevents", False)
        self.is_feed = self.script_info.get("feed", False)
        self.type = self.script_info.get("subtype") or self.script_info.get("type")
        if self.type == "python":
            self.type += "2"
        self.commands: List[CommandParser] = []
        self.connect_to_commands()
        self.connect_to_dependencies()
        self.connect_to_api_modules()
        self.connect_to_tests()

    @property
    def display_name(self) -> Optional[str]:
        return self.yml_data.get("display")

    def connect_to_commands(self) -> None:
        """Creates HAS_COMMAND relationships with the integration commands.
        Command's properties are stored in the relationship's data,
        since there will be a single node for all commands with the same name.
        """
        for command_data in self.script_info.get("commands", []):
            name = command_data.get("name")
            deprecated = command_data.get("deprecated", False) or self.deprecated
            description = command_data.get("description")
            self.add_relationship(
                RelationshipType.HAS_COMMAND,
                target=name,
                target_type=ContentType.COMMAND,
                name=name,
                deprecated=deprecated,
                description=description,
            )
            self.commands.append(
                CommandParser(name=name, description=description, deprecated=deprecated)
            )

    def connect_to_dependencies(self) -> None:
        """Collects the default classifier, mappers and incident type used as mandatory dependencies."""
        if default_classifier := self.yml_data.get("defaultclassifier"):
            if default_classifier != "null":
                self.add_dependency_by_id(
                    default_classifier, ContentType.CLASSIFIER, is_mandatory=False
                )

        if default_mapper_in := self.yml_data.get("defaultmapperin"):
            if default_mapper_in != "null":
                self.add_dependency_by_id(
                    default_mapper_in, ContentType.MAPPER, is_mandatory=False
                )

        if default_mapper_out := self.yml_data.get("defaultmapperout"):
            if default_mapper_out != "null":
                self.add_dependency_by_id(
                    default_mapper_out, ContentType.MAPPER, is_mandatory=False
                )

        if default_incident_type := self.yml_data.get("defaultIncidentType"):
            if default_incident_type != "null":
                self.add_dependency_by_id(
                    default_incident_type, ContentType.INCIDENT_TYPE, is_mandatory=False
                )

    def get_code(self) -> Optional[str]:
        """Gets the integration code.
        If the integration is unified, then it is taken from the yml file.
        Otherwise, uses the Unifier object to get it.

        Returns:
            str: The integration code.
        """
        if self.is_unified or self.script_info.get("script") not in ("-", "", None):
            return self.script_info.get("script")
        return IntegrationScriptUnifier.get_script_or_integration_package_data(
            self.path.parent
        )[1]

    def connect_to_api_modules(self) -> None:
        """Creates IMPORTS relationships with the API modules used in the integration."""
        code = self.get_code()
        if not code:
            raise ValueError("Integration code is not available")
        api_modules = IntegrationScriptUnifier.check_api_module_imports(code).values()
        for api_module in api_modules:
            self.add_relationship(
                RelationshipType.IMPORTS, api_module, ContentType.SCRIPT
            )
