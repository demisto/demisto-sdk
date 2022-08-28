from typing import Set
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class XSIAMReport(ContentItem):
    pass

    def included_in_metadata(self) -> Set[str]:
        return {'name', 'description'}
