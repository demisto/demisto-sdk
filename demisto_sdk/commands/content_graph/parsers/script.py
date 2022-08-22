import re
from pathlib import Path
from typing import List

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.integration_script import IntegrationScriptParser


EXECUTE_CMD_PATTERN = re.compile(r"execute_?command\(['\"](\w+)['\"].*", re.IGNORECASE)


class ScriptParser(IntegrationScriptParser, content_type=ContentTypes.SCRIPT):
    def __init__(self, path: Path, is_test: bool = False) -> None:
        super().__init__(path)
        print(f'Parsing {self.content_type} {self.object_id}')
        self.is_test: bool = is_test
        self.docker_image: str = self.yml_data.get('dockerimage', '')
        self.type: str = self.yml_data.get('subtype') or self.yml_data.get('type')
        self.tags: List[str] = self.yml_data.get('tags', [])
        self.code = self.get_code()
        if self.type == 'python':
            self.type += '2'

        self.connect_to_dependencies()
        self.connect_to_tests()

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.SCRIPT

    @property
    def description(self) -> str:
        return self.yml_data.get('comment', '')

    def connect_to_dependencies(self) -> None:
        for cmd in self.get_depends_on():
            self.add_dependency(cmd)

        for cmd in self.get_command_executions():
            self.add_dependency(cmd)

    def get_depends_on(self) -> List[str]:
        depends_on: List[str] = self.yml_data.get('dependson', {}).get('must', [])
        return list({cmd.split('|')[-1] for cmd in depends_on})

    def get_code(self) -> str:
        if self.is_unified or self.yml_data.get('script') not in ['-', '']:
            return self.yml_data.get('script')
        return self.unifier.get_script_or_integration_package_data()[1]

    def get_command_executions(self) -> List[str]:
        return set(EXECUTE_CMD_PATTERN.findall(self.code))
