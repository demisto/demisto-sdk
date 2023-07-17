from typing import Set

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.upload.exceptions import NotIndivitudallyUploadableException


class PreProcessRule(ContentItem, content_type=ContentType.PREPROCESS_RULE):
    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}

    def _upload(self, client, marketplace: MarketplaceVersions) -> None:
        raise NotIndivitudallyUploadableException(self)
