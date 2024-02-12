from pathlib import Path

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.upload.exceptions import NotIndivitudallyUploadableException


class PreProcessRule(ContentItem, content_type=ContentType.PREPROCESS_RULE):
    def _upload(self, client, marketplace: MarketplaceVersions) -> None:
        raise NotIndivitudallyUploadableException(self)

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if (
            "scriptName" in _dict
            and "existingEventsFilters" in _dict
            and "readyExistingEventsFilters" in _dict
            and "newEventFilters" in _dict
            and "readyNewEventFilters" in _dict
            and path.suffix == ".json"
        ):
            return True
        return False
