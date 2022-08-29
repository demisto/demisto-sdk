from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import JSONContentItemParser


class ListParser(JSONContentItemParser, content_type=ContentType.LIST):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.type = self.json_data.get('type')
