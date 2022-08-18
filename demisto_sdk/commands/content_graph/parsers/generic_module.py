from pathlib import Path

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser


class GenericModuleParser(JSONContentItemParser):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        print(f'Parsing {self.content_type} {self.object_id}')
        self.definition_id = self.json_data.get('definitionId')

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.GENERIC_MODULE
