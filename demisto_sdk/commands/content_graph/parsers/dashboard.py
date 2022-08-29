from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import JSONContentItemParser


class DashboardParser(JSONContentItemParser, content_type=ContentType.DASHBOARD):
    def __init__(self, path: Path) -> None:
        super().__init__(path)

        self.connect_to_dependencies()

    def connect_to_dependencies(self) -> None:
        """ Collects the scripts used in the dashboard as optional dependencies.
        """
        for layout in self.json_data.get('layout', []):
            widget_data = layout.get('widget')
            if widget_data.get('dataType') == 'scripts':
                if script_name := widget_data.get('query'):
                    self.add_dependency(script_name, ContentType.SCRIPT, is_mandatory=False)
