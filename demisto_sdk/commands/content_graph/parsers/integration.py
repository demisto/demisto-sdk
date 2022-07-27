from pathlib import Path
from typing import Any, Dict, List

from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel
from .integration_script import IntegrationScriptParser, IntegrationScriptUnifier
from .pack import PackSubGraphCreator


class IntegrationParser(IntegrationScriptParser):
    def __init__(self, path: Path, pack_marketplaces: List[str]) -> None:
        super().__init__(path, pack_marketplaces)
        print(f'Parsing {self.content_type} {self.content_item_id}')
        self.script_info: Dict[str, Any] = self.yml_data.get('script', {})
        PackSubGraphCreator.add_node(self)
        self.connect_to_commands()
        self.connect_to_dependencies()
        self.connect_to_tests()

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.INTEGRATION

    def get_data(self) -> Dict[str, Any]:
        integration_script_data = super().get_data()
        integration_data = {
            'display_name': self.yml_data.get('display'),
            'type': self.script_info.get('subtype') or self.script_info.get('type'),
            'docker_image': self.script_info.get('dockerimage'),
            'is_fetch': self.script_info.get('isfetch', False),
            'is_feed': self.script_info.get('feed', False),
        }

        if integration_data['type'] == 'python':
            integration_data['type'] += '2'

        return integration_script_data | integration_data

    def connect_to_commands(self) -> None:
        for command_data in self.script_info.get('commands', []):
            cmd_name = command_data.get('name')
            node_id: str = f'{ContentTypes.COMMAND}:{cmd_name}'
            deprecated: bool = command_data.get('deprecated', False) or self.deprecated
            PackSubGraphCreator.add_relationship(self, Rel.HAS_COMMAND, node_id, deprecated=deprecated)

    def connect_to_dependencies(self) -> None:
        if default_classifier := self.yml_data.get('defaultclassifier'):
            self.add_dependency(default_classifier, ContentTypes.CLASSIFIER)

        if default_mapper_in := self.yml_data.get('defaultmapperin'):
            self.add_dependency(default_mapper_in, ContentTypes.CLASSIFIER)

        if default_mapper_out := self.yml_data.get('defaultmapperout'):
            self.add_dependency(default_mapper_out, ContentTypes.CLASSIFIER)

        if default_incident_type := self.yml_data.get('defaultIncidentType'):
            self.add_dependency(default_incident_type, ContentTypes.INCIDENT_TYPE)

        for api_module in self.get_integration_api_modules():
            self.add_dependency(api_module, ContentTypes.SCRIPT)

    def get_code(self) -> str:
        if self.is_unified or self.script_info.get('script') not in ['-', '']:
            return self.script_info.get('script')
        return self.unifier.get_script_or_integration_package_data()[1]

    def get_integration_api_modules(self) -> List[str]:
        return list(IntegrationScriptUnifier.check_api_module_imports(self.get_code()).values())
