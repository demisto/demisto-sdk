from functools import cached_property
from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.content_item import (
    IncorrectParserException,
)
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)
from demisto_sdk.commands.content_graph.parsers.mapper import MapperParser


class ClassifierParser(JSONContentItemParser, content_type=ContentType.CLASSIFIER):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        git_sha: Optional[str] = None,
    ) -> None:
        """Parses the classifier.

        Args:
            path (Path): The classifier's path.

        Raises:
            IncorrectParserException: When detecting this content item is a mapper.
        """
        super().__init__(path, pack_marketplaces, git_sha=git_sha)
        self.type = self.json_data.get("type")
        if self.type != "classification":
            raise IncorrectParserException(correct_parser=MapperParser)

        self.definition_id = self.json_data.get("definitionId")
        self.connect_to_dependencies()

    @cached_property
    def field_mapping(self):
        super().field_mapping.update({"name": ["name", "brandName"]})
        return super().field_mapping

    def get_filters_and_transformers_from_complex_value(
        self, complex_value: dict
    ) -> None:
        for filter in complex_value.get("filters", []):
            if filter:
                filter_script = filter[0].get("operator").split(".")[-1]
                self.add_dependency_by_id(filter_script, ContentType.SCRIPT)

        for transformer in complex_value.get("transformers", []):
            if transformer:
                transformer_script = transformer.get("operator").split(".")[-1]
                self.add_dependency_by_id(transformer_script, ContentType.SCRIPT)

    def connect_to_dependencies(self) -> None:
        """Collects the incident types, filters and transformers used in the classifier as required dependencies."""
        if self.json_data.get("feed"):
            content_type_to_map = ContentType.INDICATOR_TYPE
        else:
            content_type_to_map = ContentType.INCIDENT_TYPE

        if default_incident_type := self.json_data.get("defaultIncidentType"):
            self.add_dependency_by_id(
                default_incident_type, content_type_to_map, is_mandatory=False
            )

        for incident_type in self.json_data.get("keyTypeMap", {}).values():
            self.add_dependency_by_id(
                incident_type, content_type_to_map, is_mandatory=False
            )

        if transformer_complex_value := self.json_data.get("transformer", {}).get(
            "complex", {}
        ):
            self.get_filters_and_transformers_from_complex_value(
                transformer_complex_value
            )

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.XSOAR_SAAS,
            MarketplaceVersions.XSOAR_ON_PREM,
        }
