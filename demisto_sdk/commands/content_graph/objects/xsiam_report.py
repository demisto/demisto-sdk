from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    ContentItemXSIAM,
)


class XSIAMReport(ContentItemXSIAM, content_type=ContentType.XSIAM_REPORT):  # type: ignore[call-arg]
    def summary(
        self,
        marketplace: Optional[MarketplaceVersions] = None,
        incident_to_alert: bool = False,
    ) -> dict:
        summary = super().summary(marketplace, incident_to_alert)
        if preview := self.get_preview_image_gcs_path():
            summary.update({"preview": preview})
        return summary

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "templates_data" in _dict and path.suffix == ".json":
            return True
        return False
