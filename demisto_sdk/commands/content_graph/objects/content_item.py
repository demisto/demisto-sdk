from pathlib import Path
from typing import List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent


class ContentItem(BaseContent):
    path: Path
    marketplaces: List[MarketplaceVersions] = []
    name: str
    from_version: str
    to_version: str
