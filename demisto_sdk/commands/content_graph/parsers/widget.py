from pathlib import Path
from typing import List

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser


class WidgetParser(JSONContentItemParser):
    def __init__(self, path: Path, pack_marketplaces: List[str]) -> None:
        super().__init__(path, pack_marketplaces)
        self.data_type = self.json_data.get('dataType')
        self.widget_type = self.json_data.get('widgetType')

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.WIDGET
