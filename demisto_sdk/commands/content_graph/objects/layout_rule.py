from typing import Set

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    ContentItemXSIAM,
)


class LayoutRule(ContentItemXSIAM, content_type=ContentType.LAYOUT_RULE):  # type: ignore[call-arg]
    def metadata_fields(self) -> Set[str]:
        return {"rule_name", "description"}
