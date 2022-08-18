from pathlib import Path
from typing import TYPE_CHECKING

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.parsers.pack import PackParser


class WidgetParser(JSONContentItemParser):
    def __init__(self, path: Path, pack: 'PackParser') -> None:
        super().__init__(path, pack)
        print(f'Parsing {self.content_type} {self.object_id}')
        self.data_type = self.json_data.get('dataType')
        self.widget_type = self.json_data.get('widgetType')

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.WIDGET

    def add_to_pack(self) -> None:
        self.pack.content_items.widget.append(self)
