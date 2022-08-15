from typing import Any, Dict, List
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript, IntegrationScriptUnifier


class Command:
    name: str
    deprecated: bool = False
    description: str

class Integration(IntegrationScript):
    display_name: str = ''
    is_fetch: bool = False
    is_feed: bool = False
    script_info: Dict[str, Any] = {}
    commands: List[Command] = []  # todo: use Command class

    def __post_init__(self) -> None:
        if self.should_parse_object:
            self.content_type =  ContentTypes.INTEGRATION
            print(f'Parsing {self.content_type} {self.object_id}')
            self.script_info = self.get_code()
            self.display_name = self.yml_data.get('display')
            self.type = self.script_info.get('subtype') or self.script_info.get('type')
            self.docker_image = self.script_info.get('dockerimage', '')
            self.is_fetch = self.script_info.get('isfetch', False)
            self.is_feed = self.script_info.get('feed', False)

            if self.type == 'python':
                self.type += '2'

            self.connect_to_commands()
            self.connect_to_dependencies()
            self.connect_to_api_modules()

    def connect_to_commands(self) -> None:
        for command_data in self.script_info.get('commands', []):
            cmd_name = command_data.get('name')
            deprecated: bool = command_data.get('deprecated', False) or self.deprecated
            self.add_relationship(
                Rel.HAS_COMMAND,
                target=cmd_name,
                deprecated=deprecated,
            )

    def connect_to_dependencies(self) -> None:
        if default_classifier := self.yml_data.get('defaultclassifier'):
            self.add_dependency(default_classifier, ContentTypes.CLASSIFIER)

        if default_mapper_in := self.yml_data.get('defaultmapperin'):
            self.add_dependency(default_mapper_in, ContentTypes.CLASSIFIER)

        if default_mapper_out := self.yml_data.get('defaultmapperout'):
            self.add_dependency(default_mapper_out, ContentTypes.CLASSIFIER)

        if default_incident_type := self.yml_data.get('defaultIncidentType'):
            self.add_dependency(default_incident_type, ContentTypes.INCIDENT_TYPE)

    def get_code(self) -> str:
        if self.is_unified or self.script_info.get('script') not in ['-', '']:
            return self.script_info.get('script')
        return self.unifier.get_script_or_integration_package_data()[1]

    def connect_to_api_modules(self) -> List[str]:
        code = self.get_code()
        api_modules = IntegrationScriptUnifier.check_api_module_imports(code).values()
        for api_module in api_modules:
            api_module_node_id = f'{ContentTypes.SCRIPT}:{api_module}'
            self.add_relationship(Rel.IMPORTS, api_module_node_id)
