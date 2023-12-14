from pathlib import Path
from typing import Set

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    ContentItemXSIAM,
)


class LayoutRule(ContentItemXSIAM, content_type=ContentType.LAYOUT_RULE):  # type: ignore[call-arg]
    layout_id: str

    def metadata_fields(self) -> Set[str]:
        return (
            super()
            .metadata_fields()
            .union(
                {
                    "rule_name",
                    "layout_id",
                }
            )
        )

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "rule_id" in _dict and path.suffix == ".json":
            return True
        return False
