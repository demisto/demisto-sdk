from pathlib import Path

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser


class WidgetParser(JSONContentItemParser):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        print(f'Parsing {self.content_type} {self.object_id}')
        self.data_type = self.json_data.get('dataType')
        self.widget_type = self.json_data.get('widgetType')

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.WIDGET
