import shutil
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Set

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.objects.pack import Pack
    from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData
    from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook

from pydantic import DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import (ContentType,
                                                       RelationshipType)
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
                return r.content_item  # type: ignore[return-value]
        return None

    @property
    def uses(self) -> List["RelationshipData"]:
        return [
            r
            for r in self.relationships_data
            if r.relationship_type == RelationshipType.USES and r.content_item == r.target
        ]

    @property
    def tested_by(self) -> List["TestPlaybook"]:
        return [
            r.content_item  # type: ignore[misc]
            for r in self.relationships_data
            if r.relationship_type == RelationshipType.TESTED_BY and r.content_item == r.target
        ]

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
        Transform the model to content item id_set.
        This is temporarily until the content graph is fully merged.

        Returns:
            dict: id_set entiity
        """
        id_set_entity = self.dict()
        id_set_entity["file_path"] = str(self.path)
        id_set_entity["pack"] = self.in_pack.name  # type: ignore[union-attr]
        return id_set_entity
