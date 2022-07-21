from constants import PACK_METADATA_FILENAME, ContentTypes, Rel

from demisto_sdk.commands.unify.integration_script_unifier import \
    IntegrationScriptUnifier
from demisto_sdk.commands.common.tools import get_json, get_yaml, get_yml_paths_in_dir

import re
import sys
import traceback

from pathlib import Path
from typing import Dict, List, Union, Optional, Any, Tuple, Type

UNIFIED_FILES_SUFFIXES = ['.yml']
EXECUTE_CMD_PATTERN = re.compile(r"execute_?command\(['\"](\w+)['\"].*")


def get_yaml_from_path(folder_path: Path, is_unified_file: bool) -> Dict[str, Union[str, List[str]]]:
    try:
        if is_unified_file:
            return get_yaml(folder_path)
        _, yaml_path = get_yml_paths_in_dir(folder_path.as_posix())
        return get_yaml(yaml_path)
    except Exception as e:
        print('Folder with err: ' + folder_path.as_posix())
        raise e


class BaseContentParser:
    def __init__(self, id_: str, content_type: ContentTypes) -> None:
        self.node_id: str = f'{content_type.value}:{id_}'
        self.content_type: ContentTypes = content_type
        print(f'Parsing {self.node_id}')

    def get_data(self) -> Dict[str, Any]:
        return {
            'id': self.node_id,
        }

    def create_node(self) -> Dict[str, Any]:
        node = {
            'labels': self.content_type.labels,
            'data': {prop: val for prop, val in self.get_data().items() if val is not None},
        }
        PackParser.nodes.append(node)

    def create_relationship(self, rel_type: Rel, target_node: str, **kwargs: Dict[str, Any]) -> None:
        relationship = {
            'from': self.node_id,
            'type': rel_type.value,
            'to': target_node,
        }
        if kwargs:
            relationship.update({'props': kwargs})
        PackParser.relationships.append(relationship)


class PackParser(BaseContentParser):
    nodes: List[Dict[str, Any]] = []
    relationships: List[Dict[str, Any]] = []
    def __init__(self, pack_folder: Path) -> None:
        super().__init__(pack_folder.parts[-1], ContentTypes.PACK)
        self.path: Path = pack_folder
        try:
            self.metadata: Dict[str, Any] = get_json(pack_folder / PACK_METADATA_FILENAME)
            self.marketplaces: List[str] = self.metadata.get('marketplaces', [])
            self.create_node()
            self.parse_pack()
        except Exception as e:
            print(traceback.format_exc())
            raise Exception(traceback.format_exc())
    
    @staticmethod
    def to_graph(path: Path) -> Tuple[List, List]:
        pack_parser: PackParser = PackParser(path)
        return pack_parser.nodes, pack_parser.relationships

    def get_data(self) -> Dict[str, Any]:
        return {
            'id': self.node_id,
            'name': self.metadata.get('name'),
            'file_path': self.path.as_posix(),
            'current_version': self.metadata.get('currentVersion'),
            'source': ['github.com', 'demisto', 'content'],  # todo
            'author': self.metadata.get('author'),
            'certification': 'certified' if self.metadata.get('support', '').lower() in ['xsoar', 'partner'] else '',
            'tags': self.metadata.get('tags', []),
            'use_cases': self.metadata.get('useCases', []),
            'categories': self.metadata.get('categories', []),
            'deprecated': self.metadata.get('deprecated', False),
            'marketplaces': self.marketplaces,
        }

    def parse_pack(self) -> None:
        for folder in ContentTypes.pack_folders(self.path):
            self.parse_pack_folder(folder)

    def parse_pack_folder(self, folder_path: Path) -> None:
        for content_item_path in folder_path.iterdir():
            if content_item := ContentItemParser.from_path(content_item_path, self.marketplaces):
                content_item.connect_to_pack(self.node_id)


class ContentItemParser(BaseContentParser):
    def __init__(
        self,
        id_: str,
        content_type: ContentTypes,
        path: Path,
        deprecated: bool,
        marketplaces: List[str],
    ) -> None:
        super().__init__(id_, content_type)
        self.path: Path = path
        self.deprecated = deprecated
        self.marketplaces: List[str] = marketplaces

    @staticmethod
    def is_package(path: Path) -> bool:
        return path.is_dir()

    @staticmethod
    def is_unified_file(path: Path) -> bool:
        return path.suffix in UNIFIED_FILES_SUFFIXES

    @staticmethod
    def is_content_item(path: Path) -> bool:
        return ContentItemParser.is_package(path) or ContentItemParser.is_unified_file(path)

    @staticmethod
    def from_path(path: Path, marketplaces: List[str]) -> Optional['ContentItemParser']:
        if not ContentItemParser.is_content_item(path):
            return None

        content_type: str = ContentTypes.by_folder(path.parts[-2]).value
        parser_class_name: str = f'{content_type}Parser'
        try:
            parser_class: Type['ContentItemParser'] = getattr(sys.modules[__name__], parser_class_name)
            return parser_class(path, marketplaces)
        except (AttributeError, TypeError):
            # parser class does not exist for this content type
            return None

    def connect_to_pack(self, pack_id: str) -> None:
        self.create_relationship(Rel.IN_PACK, pack_id)

    def add_dependency(self, dependency_id: str, dependency_type: ContentTypes, is_mandatory: bool = True) -> None:
        dependency_node_id = f'{dependency_type.value}:{dependency_id}'
        self.create_relationship(
            Rel.DEPENDS_ON,
            dependency_node_id,
            mandatorily=is_mandatory,
            deprecated=self.deprecated,
        )

    def get_data(self) -> Dict[str, Any]:
        return {
            'id': self.node_id,
            'file_path': self.path.as_posix(),
            'deprecated': self.deprecated,
            'marketplaces': self.marketplaces,
        }


class CommandParser(BaseContentParser):
    def __init__(self, cmd_data: Dict[str, Any], deprecated: bool = False) -> None:
        self.cmd_data: Dict[str, Any] = cmd_data
        self.name: str = self.cmd_data.get('name')
        self.deprecated: bool = self.cmd_data.get('deprecated', False) or deprecated
        super().__init__(self.name, ContentTypes.COMMAND)

    def get_data(self) -> Dict[str, Any]:
        return {
            'id': self.node_id,
            'name': self.name,
            'deprecated': self.deprecated,
        }


class IntegrationScriptParser(ContentItemParser):
    def __init__(self, path: Path, content_type: ContentTypes, marketplaces: List[str]) -> None:
        self.is_unified = ContentItemParser.is_unified_file(path)
        self.yml_data: Dict[str, Any] = get_yaml_from_path(path, self.is_unified)
        content_item_id: str = self.yml_data.get('commonfields', {}).get('id')
        deprecated: bool = self.yml_data.get('deprecated', False)
        marketplaces: List[str] = self.yml_data.get('marketplaces', []) or marketplaces
        super().__init__(content_item_id, content_type, path, deprecated, marketplaces)
        
        self.unifier = None if self.is_unified else IntegrationScriptUnifier(path.as_posix())

    
    def connect_to_tests(self) -> None:
        tests_playbooks: List[str] =  self.yml_data.get('tests', [])
        for test_playbook_id in tests_playbooks:
            if 'no test' not in test_playbook_id.lower():
                self.create_relationship(Rel.TESTED_BY, test_playbook_id)

    def get_data(self) -> Dict[str, Any]:
        content_item_data = super().get_data()
        integration_script_data = {
            'name': self.yml_data.get('name'),
            'from_version': self.yml_data.get('fromversion'),
            'to_version': self.yml_data.get('toversion'),
            'source': ['github'],  # todo
        }
        if to_version := integration_script_data['to_version']:
            content_item_data['id'] += f'_{to_version}'

        return content_item_data | integration_script_data


class IntegrationParser(IntegrationScriptParser):
    def __init__(self, path: Path, marketplaces: List[str]) -> None:
        super().__init__(path, ContentTypes.INTEGRATION, marketplaces)
        self.script_info: Dict[str, Any] = self.yml_data.get('script', {})
        self.integration_code = self.get_integration_code()
        self.create_node()
        self.connect_to_commands()
        self.connect_to_dependencies()
        self.connect_to_tests()

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
            self.create_relationship(Rel.HAS_COMMAND, node_id, deprecated=deprecated)

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

    def get_integration_code(self) -> str:
        if self.is_unified or self.script_info.get('script') not in ['-', '']:
            return self.script_info.get('script')
        return self.unifier.get_script_or_integration_package_data()[1]

    def get_integration_api_modules(self) -> List[str]:
        return list(IntegrationScriptUnifier.check_api_module_imports(self.integration_code).values())


class ScriptParser(IntegrationScriptParser):
    def __init__(self, path: Path, marketplaces: List[str]) -> None:
        super().__init__(path, ContentTypes.SCRIPT, marketplaces)
        self.script_code = self.get_script_code()
        self.create_node()
        self.connect_to_dependencies()
        self.connect_to_tests()

    def get_data(self) -> Dict[str, Any]:
        integration_script_data = super().get_data()
        script_data = {
            'type': self.yml_data.get('subtype') or self.yml_data.get('type'),
            'docker_image': self.yml_data.get('dockerimage'),
        }

        if script_data['type'] == 'python':
            script_data['type'] += '2'

        return integration_script_data | script_data

    def connect_to_dependencies(self) -> None:
        for cmd in self.get_depends_on():
            self.add_dependency(cmd, ContentTypes.COMMAND)

        for cmd in self.get_command_executions():
            self.add_dependency(cmd, ContentTypes.COMMAND)

    def get_depends_on(self) -> List[str]:
        depends_on: List[str] = self.yml_data.get('dependson', {}).get('must', [])
        return list({cmd.split('|')[-1] for cmd in depends_on})

    def get_script_code(self) -> str:
        if self.is_unified or self.yml_data.get('script') not in ['-', '']:
            return self.yml_data.get('script')
        return self.unifier.get_script_or_integration_package_data()[1]

    def get_command_executions(self) -> List[str]:
        return set(EXECUTE_CMD_PATTERN.findall(self.script_code, re.IGNORECASE))


class PlaybookParser(ContentItemParser):
    pass


class TestPlaybookParser(PlaybookParser):
    pass


class ClassifierParser(ContentItemParser):
    pass


class ClassifierParser(ContentItemParser):
    pass



class MapperParser(ContentItemParser):
    pass


class IncidentTypeParser(ContentItemParser):
    pass
