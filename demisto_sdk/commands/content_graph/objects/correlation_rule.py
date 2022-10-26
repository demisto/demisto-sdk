from typing import Set

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class CorrelationRule(ContentItem, content_type=ContentType.CORRELATION_RULE):  # type: ignore[call-arg]

    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}
