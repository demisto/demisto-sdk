from typing import List
from pathlib import Path
from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.constants import ContentTypes


class ContentItem(BaseContent):
    path: Path
    marketplaces: List[MarketplaceVersions] = list(MarketplaceVersions)
    name: str
    fromversion: str
    toversion: str
