from pathlib import Path
from typing import TYPE_CHECKING

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.parsers.pack import PackParser


class GenericModuleParser(JSONContentItemParser):
    def __init__(self, path: Path, pack: 'PackParser') -> None:
        super().__init__(path, pack)
        print(f'Parsing {self.content_type} {self.object_id}')
        self.definition_id = self.json_data.get('definitionId')

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.GENERIC_MODULE

    def add_to_pack(self) -> None:
        self.pack.content_items.generic_module.append(self)
