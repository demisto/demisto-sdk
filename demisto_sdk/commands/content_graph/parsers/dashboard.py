from pathlib import Path

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser


class DashboardParser(JSONContentItemParser, content_type=ContentTypes.DASHBOARD):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        print(f'Parsing {self.content_type} {self.object_id}')

        self.connect_to_dependencies()

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.DASHBOARD

    def connect_to_dependencies(self) -> None:
        for layout in self.json_data.get('layout', []):
            widget_data = layout.get('widget')
            if widget_data.get('dataType') == 'scripts':
                if script_name := widget_data.get('query'):
                    self.add_dependency(script_name, ContentTypes.SCRIPT, is_mandatory=False)
