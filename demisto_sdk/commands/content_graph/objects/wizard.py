from typing import List, Set
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Wizard(ContentItem):
    packs: List[str]
    integrations: List[str]
    playbooks: List[str]

    def included_in_metadata(self) -> Set[str]:
        return {'name', 'description'}
