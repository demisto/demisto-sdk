from pathlib import Path
from typing import List

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser


class GenericModuleParser(JSONContentItemParser):
    def __init__(self, path: Path, pack_marketplaces: List[str]) -> None:
        super().__init__(path, pack_marketplaces)
        self.description = self.json_data.get('description')
        self.definition_id = self.json_data.get('definitionId')

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.GENERIC_MODULE
