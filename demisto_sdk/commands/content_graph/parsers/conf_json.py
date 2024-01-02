from typing import List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.base_content import BaseContentParser


class ConfJSONParser(BaseContentParser):
    content_type = ContentType.CONF_JSON  # TODO check whether required

    @property
    def object_id(self) -> str:
        return "conf.json"

    @property
    def marketplaces(self) -> List[MarketplaceVersions]:
        return list(MarketplaceVersions)

    @property
    def fromversion(self) -> str:
        return "5.5.0"
