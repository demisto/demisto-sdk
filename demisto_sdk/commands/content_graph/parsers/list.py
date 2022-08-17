from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser


class ListParser(JSONContentItemParser):

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.LIST
