from typing import Set
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class List(ContentItem):
    type: str

    def included_in_metadata(self) -> Set[str]:
        return {'name'}
