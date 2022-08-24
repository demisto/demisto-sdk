from pathlib import Path

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.json_content_item import JSONContentItemParser


class WidgetParser(JSONContentItemParser, content_type=ContentTypes.WIDGET):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.data_type = self.json_data.get('dataType')
        self.widget_type = self.json_data.get('widgetType')

        self.connect_to_dependencies()

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.WIDGET
    
    def connect_to_dependencies(self) -> None:
        """ Collects the playbook used in the widget as a mandatory dependency.
        """
        if self.data_type:
            if script := self.json_data.get('query'):
                self.add_dependency(script, ContentTypes.SCRIPT)
