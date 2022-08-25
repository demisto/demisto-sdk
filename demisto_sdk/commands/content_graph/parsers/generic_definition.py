from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentTypes
from demisto_sdk.commands.content_graph.parsers.json_content_item import JSONContentItemParser

class GenericDefinitionParser(JSONContentItemParser, content_type=ContentTypes.GENERIC_DEFINITION):
    def __init__(self, path: Path) -> None:
        super().__init__(path)

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.GENERIC_DEFINITION
