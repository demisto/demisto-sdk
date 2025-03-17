from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_value
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.parsers.integration_script import (
    IntegrationScriptParser,
)
from demisto_sdk.commands.content_graph.strict_objects.integration import (
    StrictIntegration,
)
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)


@dataclass
class CommandParser:
    name: str
    deprecated: bool
    hidden: bool
    description: str
    args: List[dict]
    outputs: List[dict]
    quickaction: bool


class IntegrationParser(IntegrationScriptParser, content_type=ContentType.INTEGRATION):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        pack_supported_modules: List[str],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(
            path, pack_marketplaces, pack_supported_modules, git_sha=git_sha
        )
        self.script_info: Dict[str, Any] = self.yml_data.get("script", {})
        self.category = self.yml_data["category"]
        self.is_beta = self.yml_data.get("beta", False)
        self.is_fetch = self.script_info.get("isfetch", False)
        self.is_fetch_assets = self.script_info.get("isfetchassets", False)
        self.is_fetch_events = self.script_info.get("isfetchevents", False)
        self.is_fetch_events_and_assets = self.script_info.get(
            "isfetcheventsandassets", False
        )
        self.is_mappable = self.script_info.get("ismappable", False)
        self.is_remote_sync_in = self.script_info.get("isremotesyncin", False)
        self.is_fetch_samples = self.script_info.get("isFetchSamples", False)
        self.is_feed = self.script_info.get("feed", False)
        self.long_running = self.script_info.get("longRunning", False)
        self.supports_quick_actions = self.yml_data.get("supportsquickactions", False)
        self.commands: List[CommandParser] = []
        self.connect_to_commands()
        self.connect_to_dependencies()
        self.connect_to_tests()

    @property
    def strict_object(self):
        return StrictIntegration

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "display_name": "display",
                "docker_image": "script.dockerimage",
                "type": "script.type",
                "subtype": "script.subtype",
                "alt_docker_images": "script.alt_dockerimages",
                "params": "configuration",
            }
        )
        return super().field_mapping

    @property
    def display_name(self) -> Optional[str]:
        return get_value(self.yml_data, self.field_mapping.get("display_name", ""))

    @property
    def params(self) -> Optional[List]:
        return get_value(self.yml_data, self.field_mapping.get("params", ""), [])

    def connect_to_commands(self) -> None:
        """Creates HAS_COMMAND relationships with the integration commands.
        Command's properties are stored in the relationship's data,
        since there will be a single node for all commands with the same name.
        """
        for command_data in self.script_info.get("commands", []):
            name = command_data.get("name")
            deprecated = command_data.get("deprecated", False) or self.deprecated
            hidden = command_data.get("hidden", False)
            description = command_data.get("description")
            args = command_data.get("arguments") or []
            outputs = command_data.get("outputs") or []
            quickaction = command_data.get("quickaction", False)
            self.add_relationship(
                RelationshipType.HAS_COMMAND,
                target=name,
                target_type=ContentType.COMMAND,
                name=name,
                deprecated=deprecated,
                description=description,
                quickaction=quickaction,
            )
            self.commands.append(
                CommandParser(
                    name=name,
                    description=description,
                    deprecated=deprecated,
                    hidden=hidden,
                    args=args,
                    outputs=outputs,
                    quickaction=quickaction,
                )
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

    @property
    def code(self) -> Optional[str]:
        """Gets the integration code.
        If the integration is unified, then it is taken from the yml file.
        Otherwise, uses the Unifier object to get it.

        Returns:
            str: The integration code.
        """
        if self.is_unified or self.script_info.get("script") not in ("-", "", None):
            return self.script_info.get("script")
        if not self.git_sha:
            return IntegrationScriptUnifier.get_script_or_integration_package_data(
                self.path.parent
            )[1]
        else:
            return IntegrationScriptUnifier.get_script_or_integration_package_data_with_sha(
                self.path, self.git_sha, self.yml_data
            )[1]
