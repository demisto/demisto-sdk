from typing import Set
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Dashboard(ContentItem, content_type=ContentType.DASHBOARD):
    pass

    def included_in_metadata(self) -> Set[str]:
        return {'name'}
