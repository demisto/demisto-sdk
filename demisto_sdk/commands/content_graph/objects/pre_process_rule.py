from typing import Set

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class PreProcessRule(ContentItem, content_type=ContentType.PREPROCESS_RULE):
    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}
