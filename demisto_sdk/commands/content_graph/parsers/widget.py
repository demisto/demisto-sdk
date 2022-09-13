from pathlib import Path
from typing import List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import \
    JSONContentItemParser


class WidgetParser(JSONContentItemParser, content_type=ContentType.WIDGET):
    def __init__(self, path: Path, pack_marketplaces: List[MarketplaceVersions]) -> None:
        super().__init__(path, pack_marketplaces)
        self.data_type = self.json_data.get('dataType')
        self.widget_type = self.json_data.get('widgetType')

        self.connect_to_dependencies()

    def connect_to_dependencies(self) -> None:
        """ Collects the playbook used in the widget as a mandatory dependency.
        """
<<<<<<< HEAD
        if self.data_type == 'scripts':
            if script := self.json_data.get('query'):
                self.add_dependency_by_id(script, ContentType.SCRIPT)
=======
        if self.data_type:
            if script := self.json_data.get('query'):
                self.add_dependency(script, ContentType.SCRIPT)
>>>>>>> 093d4bb0ea69fdb6e9dd9e8880dc670c15c03165
