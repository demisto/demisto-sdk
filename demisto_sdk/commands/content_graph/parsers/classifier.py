from pathlib import Path
from typing import List
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.content_item import IncorrectParser
from demisto_sdk.commands.content_graph.parsers.json_content_item import JSONContentItemParser
from demisto_sdk.commands.content_graph.parsers.mapper import MapperParser


class ClassifierParser(JSONContentItemParser, content_type=ContentType.CLASSIFIER):
    def __init__(self, path: Path, pack_marketplaces: List[MarketplaceVersions]) -> None:
        """ Parses the classifier.

        Args:
            path (Path): The classifier's path.

        Raises:
            IncorrectParser: When detecting this content item is a mapper.
        """
        super().__init__(path, pack_marketplaces)

        self.type = self.json_data.get('type')
        if self.type != 'classification':
            raise IncorrectParser(correct_parser=MapperParser)

        self.definition_id = self.json_data.get('definitionId')
        self.connect_to_dependencies()

    @property
    def name(self) -> str:
        return self.json_data.get('name') or self.json_data.get('brandName')

    def get_filters_and_transformers_from_complex_value(self, complex_value: dict) -> None:
        for filter in complex_value.get('filters', []):
            if filter:
                filter_script = filter[0].get('operator')
                self.add_dependency(filter_script, ContentType.SCRIPT)

        for transformer in complex_value.get('transformers', []):
            if transformer:
                transformer_script = transformer.get('operator')
                self.add_dependency(transformer_script, ContentType.SCRIPT)

    def connect_to_dependencies(self) -> None:
        """ Collects the incident types, filters and transformers used in the classifier as required dependencies.
        """
        if default_incident_type := self.json_data.get('defaultIncidentType'):
            self.add_dependency(default_incident_type, ContentType.INCIDENT_TYPE)

        for incident_type in self.json_data.get('keyTypeMap', {}).values():
            self.add_dependency(incident_type, ContentType.INCIDENT_TYPE)

        if transformer_complex_value := self.json_data.get('transformer', {}).get('complex', {}):
            self.get_filters_and_transformers_from_complex_value(transformer_complex_value)
