from typing import Set

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class List(ContentItem, content_type=ContentType.LIST):  # type: ignore[call-arg]
    type: str

    def metadata_fields(self) -> Set[str]:
        return {"name"}
