from typing import List, Set

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Wizard(ContentItem, content_type=ContentType.WIZARD):  # type: ignore[call-arg]
    packs: List[str]
    integrations: List[str]
    playbooks: List[str]

    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}
