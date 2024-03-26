from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    ContentItemXSIAM,
)


class CorrelationRule(ContentItemXSIAM, content_type=ContentType.CORRELATION_RULE):  # type: ignore[call-arg]
    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if (
            "global_rule_id" in _dict
            or (isinstance(_dict, list) and _dict and "global_rule_id" in _dict[0])
        ) and path.suffix == ".yml":
            return True
        return False
