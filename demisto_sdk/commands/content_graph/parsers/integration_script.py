from abc import abstractmethod
from pathlib import Path

from demisto_sdk.commands.content_graph.parsers.content_item import YAMLContentItemParser
from demisto_sdk.commands.unify.integration_script_unifier import \
    IntegrationScriptUnifier


class IntegrationScriptParser(YAMLContentItemParser):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.is_unified = YAMLContentItemParser.is_unified_file(self.path)
        self.unifier = None if self.is_unified else IntegrationScriptUnifier(self.path.as_posix())

    @property
    def object_id(self) -> str:
        return self.yml_data.get('commonfields', {}).get('id')

    @abstractmethod
    def get_code(self) -> str:
        pass
