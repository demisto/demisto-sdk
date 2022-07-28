from abc import abstractmethod
from pathlib import Path
from typing import List

from demisto_sdk.commands.content_graph.parsers.content_item import YAMLContentItemParser

from demisto_sdk.commands.unify.integration_script_unifier import \
    IntegrationScriptUnifier


class IntegrationScriptParser(YAMLContentItemParser):
    def __init__(self, path: Path, pack_marketplaces: List[str]) -> None:
        super().__init__(path, pack_marketplaces)
        self.is_unified = YAMLContentItemParser.is_unified_file(self.path)
        self.unifier = None if self.is_unified else IntegrationScriptUnifier(self.path.as_posix())

    @property
    def content_item_id(self) -> str:
        return self.yml_data.get('commonfields', {}).get('id')

    @abstractmethod
    def get_code(self) -> str:
        pass
