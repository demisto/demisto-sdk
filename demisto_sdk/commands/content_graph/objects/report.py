from typing import Set

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Report(ContentItem, content_type=ContentType.REPORT):  # type: ignore[call-arg]

    def include_in_metadata(self) -> Set[str]:
        return {"name", "description"}
