from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentTypes
from demisto_sdk.commands.content_graph.parsers.json_content_item import JSONContentItemParser


class GenericTypeParser(JSONContentItemParser, content_type=ContentTypes.GENERIC_TYPE):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.definition_id = self.json_data.get('definitionId')

        self.connect_to_dependencies()

    def connect_to_dependencies(self) -> None:
        """ Collects the layouts used in the generic type as mandatory dependencies.
        """
        if layout := self.json_data.get('layout'):
            self.add_dependency(layout, ContentTypes.LAYOUT)
