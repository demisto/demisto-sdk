from typing import Set

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Dashboard(ContentItem, content_type=ContentType.DASHBOARD):  # type: ignore[call-arg]
    def metadata_fields(self) -> Set[str]:
        return {"name"}
