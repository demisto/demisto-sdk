from pathlib import Path
from typing import TYPE_CHECKING

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.parsers.pack import PackParser


class GenericTypeParser(JSONContentItemParser):
    def __init__(self, path: Path, pack: 'PackParser') -> None:
        super().__init__(path, pack)
        print(f'Parsing {self.content_type} {self.object_id}')
        self.definition_id = self.json_data.get('definitionId')

        self.connect_to_dependencies()

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.GENERIC_TYPE

    @property
    def description(self) -> str:
        return self.json_data.get('details')

    def connect_to_dependencies(self) -> None:
        if layout := self.json_data.get('layout'):
            self.add_dependency(layout, ContentTypes.LAYOUT)

    def add_to_pack(self) -> None:
        self.pack.content_items.generic_type.append(self)
