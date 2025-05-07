from abc import ABC
from pathlib import Path
from typing import List

import demisto_client
from packaging.version import Version
from pydantic import DirectoryPath, validator

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    MINIMUM_XSOAR_SAAS_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import (
    write_dict,
)
from demisto_sdk.commands.content_graph.common import (
    ContentType,
)
from demisto_sdk.commands.content_graph.objects.content_item import (
    ContentItem,
)
from demisto_sdk.commands.upload.exceptions import (
    NotIndivitudallyUploadableException,
)


class ContentItemXSIAM(ContentItem, ABC):
    @validator("fromversion", always=True)
    def validate_from_version(cls, v: str) -> str:
        if not v or DEFAULT_CONTENT_ITEM_FROM_VERSION == v:
            return MINIMUM_XSOAR_SAAS_VERSION
        return v

    def dump(
        self,
        dir: DirectoryPath,
        marketplace: MarketplaceVersions,
    ) -> None:
        dir.mkdir(exist_ok=True, parents=True)

        output_paths: List[Path] = []
        if Version(self.fromversion) >= Version("6.10.0"):
            # export XSIAM 1.3 items only with the external prefix
            output_paths.append(dir / f"external-{self.normalize_name}")

        elif Version(self.toversion) < Version("6.10.0"):
            # export XSIAM 1.2 items only without the external prefix
            output_paths.append(dir / self.normalize_name)
        else:
            # export 2 versions of the file, with/without the external prefix.
            output_paths.append(dir / f"external-{self.normalize_name}")
            output_paths.append(dir / self.normalize_name)

        data = self.prepare_for_upload(
            marketplace,
        )

        for file in output_paths:
            write_dict(file, data=data, handler=self.handler)

    def _upload(
        self,
        client: demisto_client,
        marketplace: MarketplaceVersions,
    ) -> None:
        """
        Uploadable XSIAM items should override this method.
        The rest will raise as default.
        """
        raise NotIndivitudallyUploadableException(self)

    def get_preview_image_gcs_path(self):
        """
        Updates the summary object with the preview image path in GCS if there is such an image in the content repo.
        This is for XSIAM dashboards and reports.
        """
        if (
            self.content_type in [ContentType.XSIAM_DASHBOARD, ContentType.XSIAM_REPORT]
            and (self.path.parent / f"{self.path.stem}_image.png").exists()
        ):
            return f"content/packs/{self.pack_id}/{self.in_pack.current_version}/{self.content_type.as_folder}/{self.path.stem}_image.png"  # type:ignore[union-attr]
        return ""
