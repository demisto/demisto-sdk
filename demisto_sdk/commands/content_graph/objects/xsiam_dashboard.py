import shutil
from typing import Set

from pydantic import DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item_xsiam import (
    ContentItemXSIAM,
)


class XSIAMDashboard(ContentItemXSIAM, content_type=ContentType.XSIAM_DASHBOARD):  # type: ignore[call-arg]
    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}

    def dump(self, dir: DirectoryPath, marketplace: MarketplaceVersions) -> None:
        super().dump(dir, marketplace)
        if (self.path.parent / f"{self.path.stem}_image.png").exists():
            shutil.copy(
                self.path.parent / f"{self.path.stem}_image.png",
                dir / f"{self.path.stem}_image.png",
            )
