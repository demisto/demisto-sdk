from typing import Set

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_x2 import ContentItemX2


class XSIAMReport(ContentItemX2, content_type=ContentType.XSIAM_REPORT):  # type: ignore[call-arg]

    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}
