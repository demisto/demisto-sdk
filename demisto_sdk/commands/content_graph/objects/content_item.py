import shutil
from typing import List, Optional
from pathlib import Path

from pydantic import DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.constants import ContentTypes


class ContentItem(BaseContent):
    path: Path
    marketplaces: List[MarketplaceVersions]
    name: str
    fromversion: str
    toversion: str
    deprecated: bool
    description: Optional[str]

    def normalize_file_name(self, name: str) -> str:
        for prefix in ContentTypes.prefixes():
            name = name.replace(f'{prefix}-', '')
        
        return f'{self.content_type.prefix}-{name}'

    def dump(self, dir: DirectoryPath, _: MarketplaceVersions) -> None:
        dir.mkdir(exist_ok=True, parents=True)
        shutil.copy(self.path, dir / self.normalize_file_name(self.path.name))
