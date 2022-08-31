import logging

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.content_item import ContentItemParser


logger = logging.getLogger('demisto-sdk')


class ContentItemsList(list):
    """ An extension for list - a list of a specific content type.

    Attributes:
        content_type (ContentType): The content types allowed to be included in this list.
    """
    def __init__(self, content_type: ContentType):
        self.content_type: ContentType = content_type
        super().__init__()

    def append_conditionally(self, content_item: ContentItemParser) -> bool:
        """ Appends if the content item is in the correct type.

        Args:
            content_item (ContentItemParser): The content item.

        Returns:
            bool: True iff the content item was appended.
        """
        if isinstance(content_item, ContentItemParser) and content_item.content_type == self.content_type:
            self.append(content_item)
            return True
        return False
