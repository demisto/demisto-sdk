import shutil
from functools import cached_property
from pathlib import Path
from typing import Optional

from pydantic import DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    ContentItemXSIAM,
)
from demisto_sdk.commands.content_graph.parsers.related_files import ImageRelatedFile


class XSIAMDashboard(ContentItemXSIAM, content_type=ContentType.XSIAM_DASHBOARD):  # type: ignore[call-arg]
    def summary(
        self,
        marketplace: Optional[MarketplaceVersions] = None,
        incident_to_alert: bool = False,
    ) -> dict:
        summary = super().summary(marketplace, incident_to_alert)
        if preview := self.get_preview_image_gcs_path():
            summary.update({"preview": preview})
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

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "dashboards_data" in _dict and path.suffix == ".json":
            return True
        return False

    @cached_property
    def image(self) -> ImageRelatedFile:
        return ImageRelatedFile(self.path, git_sha=self.git_sha)
