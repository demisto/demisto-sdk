from typing import Set
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Trigger(ContentItem, content_type=ContentType.TRIGGER):
    pass

    def included_in_metadata(self) -> Set[str]:
        return {'name', 'description'}
