import nodes
from constants import PackFolder, PACKS_FOLDER, PACK, COMMAND

from demisto_sdk.commands.unify.integration_script_unifier import \
    IntegrationScriptUnifier
from demisto_sdk.commands.common.tools import get_json, get_yaml, get_yml_paths_in_dir

import re
import traceback
from pathlib import Path
from typing import Dict, List, Type, Union, Optional, Any

from multiprocessing import cpu_count, Manager

PROCESSES_COUNT = cpu_count() - 1


def get_yaml_in_folder(folder_path: Path, is_unified_file: bool) -> Dict[str, Union[str, List[str]]]:
    try:
        if is_unified_file:
            return get_yaml(folder_path)
        _, yaml_path = get_yml_paths_in_dir(folder_path.as_posix())
        return get_yaml(yaml_path)
    except Exception as e:
        print('Folder with err: ' + folder_path.as_posix())
        raise e


class BaseContentParser:
    def __init__(self, id_: str) -> None:
        print(f'Parsing {id_}')
        self.id_: str = id_
    
    def get_data(self) -> Dict[str, Any]:
        return {
            'id': self.id_,
        }


class PackParser(BaseContentParser):
    PACK_METADATA_FILENAME = 'pack_metadata.json'
    def __init__(self, pack_folder: Path) -> None:
        super().__init__(id_=f'{PACK}:{pack_folder.parts[-1]}')
        self.path = pack_folder
        try:
            self.metadata = get_json(pack_folder / self.PACK_METADATA_FILENAME)
            self.marketplaces = self.metadata.get('marketplaces', [])
            self.node = nodes.PackNode.create_or_update(self.get_data())
            self.parse_pack()
        except Exception as e:
            print(traceback.format_exc())
            raise e

    def get_data(self) -> Dict[str, Any]:
        pack_data = {
            'name': self.metadata.get('name'),
            'file_path': self.path.as_posix(),
            'current_version': self.metadata.get('currentVersion'),
            'source': ['github.com', 'demisto', 'content'],  # todo
            'author': self.metadata.get('author', ''),
            'certification': 'certified' if self.metadata.get('support', '').lower() in ['xsoar', 'partner'] else '',
            'tags': self.metadata.get('tags', []),
            'use_cases': self.metadata.get('useCases', []),
            'categories': self.metadata.get('categories', []),
            'deprecated': self.metadata.get('deprecated', False),
            'marketplaces': self.marketplaces,
        }
        pack_data.update(super().get_data())
        return pack_data

    def parse_pack(self) -> None:
        for folder in self.path.iterdir():
            if folder.is_dir() and PackFolder.has_value(folder.parts[-1]):
                self.parse_pack_folder(folder)

    def parse_pack_folder(self, folder_path: Path) -> None:
        for content_item in folder_path.iterdir():
            if content_item_parser := ContentItemParser.from_path(content_item, self.marketplaces):
                self.node.content_items.connect(content_item_parser.node)


class ContentItemParser(BaseContentParser):
    def __init__(self, id_: str, content_type: str, path: Path, marketplaces: List[str]) -> None:
        super().__init__(id_=f'{content_type}:{id_}')
        self.type = content_type
        self.name = id_
        self.path = path
        self.marketplaces = marketplaces
        self.dependencies: List[str] = []

    @staticmethod
    def by_folder(folder: PackFolder) -> Type['ContentItemParser']:
        folder_to_parser = {
            PackFolder.INTEGRATIONS: IntegrationParser,
            PackFolder.SCRIPTS: ScriptParser,
        }
        return folder_to_parser.get(folder)

    @staticmethod
    def from_path(path: Path, marketplaces: List[str]) -> Optional['ContentItemParser']:
        folder = PackFolder(path.parts[-2])
        if parser := ContentItemParser.by_folder(folder):
            if parser.is_content_item_package(path):
                return parser(path, marketplaces)

            elif parser.is_unified_content_item(path):
                return parser(path, marketplaces, is_unified_file=True)

        return None

    @staticmethod
    def is_content_item_package(path: Path) -> bool:
        return path.is_dir()
    
    @staticmethod
    def is_unified_content_item(path: Path) -> bool:
        return path.suffix in ['.yml']

    def add_dependency(self, content_type: str, content_item_id) -> None:
        self.dependencies.append(f'{content_type}:{content_item_id}')
    
    def get_data(self) -> Dict[str, Any]:
        content_item_data = {
            'name': self.name,
            'dependencies_ids': self.dependencies,
            'file_path': self.path.as_posix(),
            'marketplaces': self.marketplaces,
        }
        content_item_data.update(super().get_data())
        return content_item_data


class CommandParser(BaseContentParser):
    def __init__(self, cmd_data: Dict[str, Any], deprecated: bool = False) -> None:
        self.cmd_data = cmd_data
        self.name = self.cmd_data.get('name')
        self.deprecated = self.cmd_data.get('deprecated', False) or deprecated
        super().__init__(id_=f'{COMMAND}:{self.name}')
        self.node = nodes.CommandNode.create_or_update(self.get_data())

    def get_data(self) -> Dict[str, Any]:
        command_data = {
            'name': self.name,
            'deprecated': self.deprecated,
        }
        command_data.update(super().get_data())
        return command_data


class IntegrationScriptParser(ContentItemParser):
    def __init__(self, folder_path: Path, content_type: str, marketplaces: List[str], is_unified_file: bool = False) -> None:
        self.yml_data = get_yaml_in_folder(folder_path, is_unified_file)
        id_ = self.yml_data.get('commonfields', {}).get('id', '-')
        marketplaces = self.yml_data.get('marketplaces', []) or marketplaces
        super().__init__(id_, content_type, folder_path, marketplaces)
        self.script = self.yml_data.get('script', {})
        self.deprecated = self.yml_data.get('deprecated', False)
        self.unifier = IntegrationScriptUnifier(folder_path.as_posix()) if not is_unified_file else None

    def get_data(self) -> Dict[str, Any]:
        integration_script_data = {
            'name': self.yml_data.get('name', '-'),
            'display_name': self.yml_data.get('display', '-'),
            'deprecated': self.deprecated,
            'tests': self.yml_data.get('tests'),
            'toversion': self.yml_data.get('toversion'),
            'fromversion': self.yml_data.get('fromversion'),
            'source': ['github'],  # todo
        }
        integration_script_data.update(super().get_data())
        return integration_script_data



class IntegrationParser(IntegrationScriptParser):
    def __init__(self, folder_path: Path, marketplaces: List[str], is_unified_file: bool = False) -> None:
        super().__init__(folder_path, PackFolder.INTEGRATIONS.type, marketplaces, is_unified_file)
        self.get_dependencies_ids()
        self.node = nodes.IntegrationNode.create_or_update(self.get_data())
        self.parse_integration_commands()

    def get_data(self) -> Dict[str, Any]:
        integration_data = {
            'type': self.script.get('subtype') or self.script.get('type'),
            'docker_image': self.script.get('dockerimage'),
            'is_fetch': self.script.get('isfetch', False),
            'is_feed': self.script.get('feed', False),
        }
        if integration_data['type'] == 'python':
            integration_data['type'] += '2'

        integration_data.update(super().get_data())
        return integration_data

    def parse_integration_commands(self) -> None:
        for command_data in self.script.get('commands', []):
            cmd = CommandParser(command_data, self.deprecated)
            self.node.commands.connect(cmd.node)
    
    def get_dependencies_ids(self) -> None:
        if default_classifier := self.yml_data.get('defaultclassifier'):
            self.add_dependency(PackFolder.CLASSIFIERS.type, default_classifier)

        if default_mapper_in := self.yml_data.get('defaultmapperin'):
            self.add_dependency(PackFolder.CLASSIFIERS.type, default_mapper_in)

        if default_mapper_out := self.yml_data.get('defaultmapperout'):
            self.add_dependency(PackFolder.CLASSIFIERS.type, default_mapper_out)

        if default_incident_type := self.yml_data.get('defaultIncidentType'):
            self.add_dependency(PackFolder.INCIDENT_TYPES.type, default_incident_type)

        if api_module := self.get_integration_api_module():
            self.add_dependency(PackFolder.SCRIPTS.type, api_module)

    def get_integration_api_module(self) -> Optional[str]:
        integration_code = self.yml_data.get('script', {}).get('script', '')
        if not integration_code:
            if self.unifier:
                _, integration_code = self.unifier.get_script_or_integration_package_data()
            else:
                return None  # todo: raise exception?

        return IntegrationScriptUnifier.check_api_module_imports(integration_code)[1]


class ScriptParser(IntegrationScriptParser):
    def __init__(self, folder_path: Path, marketplaces: List[str], is_unified_file: bool = False) -> None:
        super().__init__(folder_path, PackFolder.SCRIPTS.type, marketplaces, is_unified_file)
        self.get_dependencies_ids()
        self.node = nodes.ScriptNode.create_or_update(self.get_data())

    def get_data(self) -> Dict[str, Any]:
        script_data = {
            'type': self.yml_data.get('subtype') or self.yml_data.get('type'),
            'docker_image': self.yml_data.get('dockerimage'),
        }
        if script_data['type'] == 'python':
            script_data['type'] += '2'

        script_data.update(super().get_data())
        return script_data

    def get_dependencies_ids(self) -> None:
        for cmd in self.get_depends_on():
            self.add_dependency(COMMAND, cmd)

        for cmd in self.get_command_executions():
            self.add_dependency(COMMAND, cmd)

    def get_depends_on(self) -> List[str]:
        depends_on = self.yml_data.get('dependson', {}).get('must', [])
        return list({cmd.split('|')[-1] for cmd in depends_on})

    def get_command_executions(self) -> List[str]:
        if not self.script:
            if self.unifier:
                _, self.script = self.unifier.get_script_or_integration_package_data()
            else:
                return []  # todo: raise exception?

        return sorted(list(set(re.findall(r"execute_?command\(['\"](\w+)['\"].*", self.script, re.IGNORECASE))))


class ClassifierParser(ContentItemParser):
    pass


class MapperParser(ContentItemParser):
    pass


class IncidentTypeParser(ContentItemParser):
    pass


class RepositoryParser:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = Path(repo_path)
        self.packs_path = self.repo_path / PACKS_FOLDER
        self.packs: List[PackParser] = []

    def run(self) -> None:
        self.parse_repository()
    
    def parse_repository(self) -> None:
        packs_directories = [p for p in self.packs_path.iterdir() if p.is_dir()]
        with Manager() as manager:
            pool = manager.Pool(processes=PROCESSES_COUNT)
            for pack in pool.map(PackParser, packs_directories):
                self.packs.append(pack)
