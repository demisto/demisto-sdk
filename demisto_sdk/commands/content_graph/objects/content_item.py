import shutil
from typing import List, Optional, Set
from pathlib import Path

from pydantic import DirectoryPath, Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.common import ContentType



class ContentItem(BaseContent):
    path: Path
    marketplaces: List[MarketplaceVersions]
    name: str
    fromversion: str
    toversion: str
    deprecated: bool
    description: Optional[str]

    def summary(self) -> dict:
        return self.dict(include=self.included_in_metadata(), by_alias=True)

    def included_in_metadata(self) -> Set[str]:
        raise NotImplementedError('Should be implemented in subclasses')

    def normalize_file_name(self, name: str) -> str:
        for prefix in ContentTypes.prefixes():
            name = name.replace(f'{prefix}-', '')

        return f'{self.content_type.prefix}-{name}'

    def dump(self, dir: DirectoryPath, _: MarketplaceVersions) -> None:
        dir.mkdir(exist_ok=True, parents=True)
        shutil.copy(self.path, dir / self.normalize_file_name(self.path.name))
