from pathlib import Path
from typing import Any, Dict, List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType, Relationship
from demisto_sdk.commands.content_graph.parsers.integration_script import (
    IntegrationScriptParser,
    IntegrationScriptUnifier
)


class IntegrationParser(IntegrationScriptParser, content_type=ContentType.INTEGRATION):
    def __init__(self, path: Path, pack_marketplaces: List[MarketplaceVersions]) -> None:
        super().__init__(path, pack_marketplaces)
        self.script_info: Dict[str, Any] = self.yml_data.get('script', {})
        self.category = self.yml_data['category']
        self.display_name = self.yml_data['display']
        self.docker_image = self.script_info.get('dockerimage', '')
        self.is_fetch = self.script_info.get('isfetch', False)
        self.is_feed = self.script_info.get('feed', False)
        self.type = self.script_info.get('subtype') or self.script_info.get('type')
        if self.type == 'python':
            self.type += '2'

        self.connect_to_commands()
        self.connect_to_dependencies()
        self.connect_to_api_modules()
        self.connect_to_tests()

    def connect_to_commands(self) -> None:
        """ Creates HAS_COMMAND relationships with the integration commands.
        Command's properties are stored in the relationship's data,
        since there will be a single node for all commands with the same name.
        """
        for command_data in self.script_info.get('commands', []):
            self.add_relationship(
                Relationship.HAS_COMMAND,
                target=command_data.get('name'),
                name=command_data.get('name'),
                deprecated=command_data.get('deprecated', False) or self.deprecated,
                description=command_data.get('description')
            )

    def connect_to_dependencies(self) -> None:
        """ Collects the default classifier, mappers and incident type used as mandatory dependencies.
        """
        if default_classifier := self.yml_data.get('defaultclassifier'):
            if default_classifier != 'null':
                self.add_dependency(default_classifier, ContentType.CLASSIFIER)

        if default_mapper_in := self.yml_data.get('defaultmapperin'):
            if default_mapper_in != 'null':
                self.add_dependency(default_mapper_in, ContentType.MAPPER)

        if default_mapper_out := self.yml_data.get('defaultmapperout'):
            if default_mapper_out != 'null':
                self.add_dependency(default_mapper_out, ContentType.MAPPER)

        if default_incident_type := self.yml_data.get('defaultIncidentType'):
            if default_incident_type != 'null':
                self.add_dependency(default_incident_type, ContentType.INCIDENT_TYPE)

    def get_code(self) -> str:
        """ Gets the integration code.
        If the integration is unified, simply takes it from the yml file.
        Otherwise, uses the Unifier object to get it.

        Returns:
            str: The integration code.
        """
        if self.is_unified or self.script_info.get('script') not in ['-', '']:
            return self.script_info.get('script')
        return self.unifier.get_script_or_integration_package_data()[1]

    def connect_to_api_modules(self) -> List[str]:
        """ Creates IMPORTS relationships with the API modules used in the integration.
        """
        api_modules = IntegrationScriptUnifier.check_api_module_imports(self.get_code()).values()
        for api_module in api_modules:
            api_module_node_id = f'{ContentType.SCRIPT}:{api_module}'
            self.add_relationship(Relationship.IMPORTS, api_module_node_id)
