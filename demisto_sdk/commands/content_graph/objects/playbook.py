from typing import Set
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Playbook(ContentItem):
    is_test: bool

    def included_in_metadata(self) -> Set[str]:
        return {'name', 'description'}
