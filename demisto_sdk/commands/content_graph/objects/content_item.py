import shutil
from pathlib import Path
from typing import List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.objects.pack import Pack

from pydantic import DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent


class ContentItem(BaseContent):
    path: Path
    marketplaces: List[MarketplaceVersions]
    name: str
    fromversion: str
    toversion: str
    display_name: str
    deprecated: bool
    description: Optional[str]
    
    @property
    def in_pack(self) -> Optional["Pack"]:
        for r in self.relationships_data:
            if r.relationship_type == RelationshipType.IN_PACK:
                return r.related_to  # type: ignore[return-value]
        return None

    def summary(self) -> dict:
        return self.dict(include=self.metadata_fields(), by_alias=True)

    def metadata_fields(self) -> Set[str]:
        raise NotImplementedError("Should be implemented in subclasses")

    def normalize_file_name(self, name: str) -> str:
        """
        This will add the server prefix of the content item to its name
        In addition it will remove the existing server_names of the name.
        
        Args:
            name (str): content item name.
        Returns:
            str: The normalized name.        
        """
        
        for prefix in ContentType.server_names():
            name = name.replace(f"{prefix}-", "")

        return f"{self.content_type.server_name}-{name}"

    def dump(self, dir: DirectoryPath, _: MarketplaceVersions) -> None:
        dir.mkdir(exist_ok=True, parents=True)
        shutil.copy(self.path, dir / self.normalize_file_name(self.path.name))

    def to_id_set_entity(self) -> dict:
        """
        Tranfrom the model to content item id_set.
        This is temporarily until the content graph is fully merged.

        Returns:
            dict: id_set entiity
        """
        id_set_entity = self.dict()
        id_set_entity["file_path"] = str(self.path)
        id_set_entity["pack"] = self.in_pack.name
        return id_set_entity
