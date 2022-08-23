from pathlib import Path
from typing import Any, Dict, List

from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel
from demisto_sdk.commands.content_graph.parsers.integration_script import (
    IntegrationScriptParser,
    IntegrationScriptUnifier
)


class IntegrationParser(IntegrationScriptParser, content_type=ContentTypes.INTEGRATION):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
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

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.INTEGRATION

    def connect_to_commands(self) -> None:
        for command_data in self.script_info.get('commands', []):
            self.add_relationship(
                Rel.HAS_COMMAND,
                target=command_data.get('name'),
                name=command_data.get('name'),
                deprecated=command_data.get('deprecated', False) or self.deprecated,
                description=command_data.get('description')
            )

    def connect_to_dependencies(self) -> None:
        if default_classifier := self.yml_data.get('defaultclassifier'):
            if default_classifier != 'null':
                self.add_dependency(default_classifier, ContentTypes.CLASSIFIER)

        if default_mapper_in := self.yml_data.get('defaultmapperin'):
            if default_mapper_in != 'null':
                self.add_dependency(default_mapper_in, ContentTypes.MAPPER)

        if default_mapper_out := self.yml_data.get('defaultmapperout'):
            if default_mapper_out != 'null':
                self.add_dependency(default_mapper_out, ContentTypes.MAPPER)

        if default_incident_type := self.yml_data.get('defaultIncidentType'):
            if default_incident_type != 'null':
                self.add_dependency(default_incident_type, ContentTypes.INCIDENT_TYPE)

    def get_code(self) -> str:
        if self.is_unified or self.script_info.get('script') not in ['-', '']:
            return self.script_info.get('script')
        return self.unifier.get_script_or_integration_package_data()[1]

    def connect_to_api_modules(self) -> List[str]:
        api_modules = IntegrationScriptUnifier.check_api_module_imports(self.get_code()).values()
        for api_module in api_modules:
            api_module_node_id = f'{ContentTypes.SCRIPT}:{api_module}'
            self.add_relationship(Rel.IMPORTS, api_module_node_id)
