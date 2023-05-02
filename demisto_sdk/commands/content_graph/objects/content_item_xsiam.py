from abc import ABC
from typing import Union

import demisto_client
from packaging.version import Version
from pydantic import DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.content_item import (
    ContentItem,
    NotIndivitudallyUploadableException,
)


class ContentItemXSIAM(ContentItem, ABC):
    def dump(
        self,
        dir: DirectoryPath,
        marketplace: MarketplaceVersions,
        dump_into_list: bool = False,
    ) -> None:
        dir.mkdir(exist_ok=True, parents=True)

        output_paths = []
        data: Union[list, dict] = self.prepare_for_upload(marketplace)

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

        if dump_into_list:
            data = [data]

        for file in output_paths:
            with open(file, "w") as f:
                self.handler.dump(data, f)

    def _upload(
        self,
        client: demisto_client,
        marketplace: MarketplaceVersions,
        dump_into_list: bool = False,
    ) -> None:
        """
        Uploadable XSIAM items should override this method.
        The rest will raise as default.
        """
        raise NotIndivitudallyUploadableException(self)
