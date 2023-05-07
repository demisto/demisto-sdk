from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.content_item import ContentItemParser


class ContentItemsList(list):
    """An extension for list - a list of a specific content type.

    Attributes:
        content_type (ContentType): The content types allowed to be included in this list.
    """

    def __init__(self, content_type: ContentType):
        self.content_type: ContentType = content_type
        super().__init__()

    def __eq__(self, __o: object) -> bool:
        return super().__eq__(__o)

    def append(self, content_item: ContentItemParser) -> None:
        """Appends if the content item is in the correct type.

        Args:
            content_item (ContentItemParser): The content item.
        """
        if content_item.content_type != self.content_type:
            raise TypeError(
                f"{content_item.node_id}: Expected a ContentItemParser of type {self.content_type}"
            )
        super().append(content_item)
