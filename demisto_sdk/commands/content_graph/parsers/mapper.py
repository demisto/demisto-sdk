from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)

IGNORED_INCIDENT_TYPES = ["dbot_classification_incident_type_all"]


class MapperParser(JSONContentItemParser, content_type=ContentType.MAPPER):
    def __init__(
        self, path: Path, pack_marketplaces: List[MarketplaceVersions]
    ) -> None:
        super().__init__(path, pack_marketplaces)
        self.type = self.json_data.get("type")
        self.definition_id = self.json_data.get("definitionId")
        self.connect_to_dependencies()

    @property
    def name(self) -> Optional[str]:
        return self.json_data.get("name") or self.json_data.get("brandName")

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2}

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
        """Collects the incident types, incident fields, filters and transformers
        used in the mapper as required dependencies.
        """
        if self.json_data.get("feed"):
            content_type_to_map = ContentType.INDICATOR_TYPE
            fields_content_type = ContentType.INDICATOR_FIELD
            add_dependency_func = self.add_dependency_by_id
        else:
            content_type_to_map = ContentType.INCIDENT_TYPE
            fields_content_type = ContentType.INCIDENT_FIELD
            add_dependency_func = self.add_dependency_by_name  # type: ignore

        if default_incident_type := self.json_data.get("defaultIncidentType"):
            add_dependency_func(
                default_incident_type, content_type_to_map, is_mandatory=False
            )

        for incident_type, mapping_data in self.json_data.get("mapping", {}).items():
            if incident_type not in IGNORED_INCIDENT_TYPES:
                add_dependency_func(
                    incident_type, content_type_to_map, is_mandatory=False
                )
            internal_mapping: Dict[str, Any] = mapping_data.get("internalMapping")

            if self.type == "mapping-outgoing":
                # incident fields are in the simple / complex.root key of each key
                for fields_mapper in internal_mapping.values():
                    if isinstance(fields_mapper, dict):
                        if incident_field_simple := fields_mapper.get("simple"):
                            self.add_dependency_by_id(
                                incident_field_simple,
                                fields_content_type,
                                is_mandatory=False,
                            )
                        elif incident_field_complex := fields_mapper.get(
                            "complex", {}
                        ).get("root"):
                            self.add_dependency_by_id(
                                incident_field_complex,
                                fields_content_type,
                                is_mandatory=False,
                            )

            elif self.type == "mapping-incoming":
                # all the incident fields are the keys of the mapping
                for incident_field in internal_mapping.keys():
                    self.add_dependency_by_name(
                        incident_field,
                        fields_content_type,
                        is_mandatory=False,
                    )
            else:
                raise ValueError(
                    f'{self.node_id}: Unknown type "{self.type}" - expected "mapping-outgoing" or "mapping-incoming".'
                )

            for internal_mapping in internal_mapping.values():
                if incident_field_complex := internal_mapping.get("complex", {}):
                    self.get_filters_and_transformers_from_complex_value(
                        incident_field_complex
                    )
