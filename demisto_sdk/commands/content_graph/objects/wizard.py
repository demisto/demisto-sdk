from typing import List

from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Wizard(ContentItem):
    packs: List[str]
    integrations: List[str]
    playbooks: List[str]
