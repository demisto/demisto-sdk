from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    ContentItemXSIAM,
)


class CorrelationRule(ContentItemXSIAM, content_type=ContentType.CORRELATION_RULE):  # type: ignore[call-arg]
    pass
