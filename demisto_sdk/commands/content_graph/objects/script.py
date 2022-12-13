import logging
from pathlib import Path
from typing import List, Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript

logger = logging.getLogger('demisto-sdk')


class Script(IntegrationScript, content_type=ContentType.SCRIPT):  # type: ignore[call-arg]
    tags: List[str]

    def metadata_fields(self) -> Set[str]:
        return {"name", "description", "tags"}

    def dump(self, dir: Path, marketplace: MarketplaceVersions) -> None:
        if self.is_test:
            return
        return super().dump(dir, marketplace)

    def prepare_for_upload(self, marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR, **kwargs) -> dict:
        data = super().prepare_for_upload(marketplace, **kwargs)

        if marketplace == MarketplaceVersions.MarketplaceV2:
            x2_suffix = '_x2'
            len_x2_suffix = len(x2_suffix)
            for current_key in data.keys():
                if current_key.casefold().endswith(x2_suffix):
                    current_key_no_suffix = current_key[:-len_x2_suffix]
                    logger.debug(f'Replacing {current_key_no_suffix} value from {data[current_key_no_suffix]} to {data[current_key]}.')
                    data[current_key_no_suffix] = data[current_key]
        return data
