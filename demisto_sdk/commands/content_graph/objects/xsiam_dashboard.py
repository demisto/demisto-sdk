import shutil
from typing import Optional

from pydantic import DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    ContentItemXSIAM,
)


class XSIAMDashboard(ContentItemXSIAM, content_type=ContentType.XSIAM_DASHBOARD):  # type: ignore[call-arg]
    def summary(
        self,
        marketplace: Optional[MarketplaceVersions] = None,
        incident_to_alert: bool = False,
    ) -> dict:
        summary = super().summary(marketplace, incident_to_alert)
        self.update_preview_image_gcs_path(content_item_summary=summary)
        return summary

    def dump(
        self,
        dir: DirectoryPath,
        marketplace: MarketplaceVersions,
    ) -> None:
        super().dump(dir, marketplace)
        if (self.path.parent / f"{self.path.stem}_image.png").exists():
            shutil.copy(
                self.path.parent / f"{self.path.stem}_image.png",
                dir / f"{self.path.stem}_image.png",
            )
