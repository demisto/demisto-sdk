from abc import abstractmethod
from pathlib import Path

from demisto_sdk.commands.content_graph.parsers.yaml_content_item import YAMLContentItemParser
from demisto_sdk.commands.unify.integration_script_unifier import \
    IntegrationScriptUnifier


class IntegrationScriptParser(YAMLContentItemParser):
    def __init__(self, path: Path) -> None:
        self.is_unified = YAMLContentItemParser.is_unified_file(path)
        # IntegrationScriptUnifier must accept a directory path
        self.unifier = None if self.is_unified else IntegrationScriptUnifier(path.as_posix())
        # after super().__init__(), self.path will be the integration's yml path
        super().__init__(path)

    @property
    def object_id(self) -> str:
        return self.yml_data.get('commonfields', {}).get('id')

    @abstractmethod
    def get_code(self) -> str:
        pass
