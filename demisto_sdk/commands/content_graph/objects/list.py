from typing import Set

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class List(ContentItem, content_type=ContentType.LIST):
    type: str

    def included_in_metadata(self) -> Set[str]:
        return {'name'}
