from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentTypes
from demisto_sdk.commands.content_graph.parsers.json_content_item import JSONContentItemParser


class ReportParser(JSONContentItemParser, content_type=ContentTypes.REPORT):
    def __init__(self, path: Path) -> None:
        super().__init__(path)

        self.connect_to_dependencies()

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.REPORT

    def connect_to_dependencies(self) -> None:
        """ Collects scripts used in the report as optional dependencies.
        """
        for layout in self.json_data.get('dashboard', {}).get('layout', []):
            widget_data = layout.get('widget')
            if widget_data.get('dataType') == 'scripts':
                if script_name := widget_data.get('query'):
                    self.add_dependency(script_name, ContentTypes.SCRIPT, is_mandatory=False)
