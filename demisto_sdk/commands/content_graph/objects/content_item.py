import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Type

from pydantic import DirectoryPath
from demisto_sdk.commands.common.tools import get_pack_name

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent


content_type_to_model: Dict[ContentType, Type['ContentItem']] = {}


class ContentItem(BaseContent):
    path: Path
    marketplaces: List[MarketplaceVersions]
    name: str
    fromversion: str
    toversion: str
    display_name: str
    deprecated: bool
    description: Optional[str]

    def summary(self) -> dict:
        return self.dict(include=self.included_in_metadata(), by_alias=True)

    def included_in_metadata(self) -> Set[str]:
        raise NotImplementedError('Should be implemented in subclasses')

    def normalize_file_name(self, name: str) -> str:
        for prefix in ContentType.prefixes():
            name = name.replace(f'{prefix}-', '')

        return f'{self.content_type.server_name}-{name}'

    def dump(self, dir: DirectoryPath, _: MarketplaceVersions) -> None:
        dir.mkdir(exist_ok=True, parents=True)
        shutil.copy(self.path, dir / self.normalize_file_name(self.path.name))

    def to_id_set_entity(self) -> dict:
        id_set_entity = self.dict()
        id_set_entity['file_path'] = str(self.path)
        id_set_entity['pack'] = get_pack_name(self.path)
        return id_set_entity
