from datetime import datetime
from packaging.version import Version, parse
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any, Dict, List

from demisto_sdk.commands.common.tools import get_json
from demisto_sdk.commands.content_graph.constants import (
    ContentTypes,
    Rel,
    PACK_METADATA_FILENAME,
    RelationshipData,
    NodeData
)
from demisto_sdk.commands.content_graph.objects.content_item_factory import ContentItemFactory
import demisto_sdk.commands.content_graph.objects.base_content as base_content


class PackMetadata(BaseModel):
    name: str = ''
    description: str = ''
    created: datetime = datetime.utcnow()
    updated: datetime = datetime.utcnow()
    legacy: bool = True
    support: str = ''
    eula_link: str = Field(
        'https://github.com/demisto/content/blob/master/LICENSE',
        alias='eulaLink',
    )
    email: str = ''
    url: str = ''
    author: str = ''
    certification: str = ''
    price: int = 0
    premium: bool = False
    vendor_id: str = Field('', alias='vendorId')
    vendor_name: str = Field('', alias='vendorName')
    hidden: bool = False
    preview_only: bool = Field(False, alias='previewOnly')
    server_min_version: Version = Field(
        parse('0.0.0'),
        alias='serverMinVersion',
    )
    current_version: Version = Field(
        parse('0.0.0'),
        alias='currentVersion',
    )
    version_info: int = Field(0, alias='versionInfo')
    tags: List[str] = []
    categories: List[str] = []
    use_cases: List[str] = Field([], alias='useCases')
    keywords: List[str] = []


class Pack(base_content.BaseContent):
    path: Path = ...
    metadata: PackMetadata = None
    content_items: Dict[ContentTypes, List] = Field({}, alias='contentItems')
    relationships: Dict[Rel, List[RelationshipData]] = {}

    def __post_init__(self):
        if self.should_parse_object:
            self.object_id = self.path.parts[-1]
            self.content_type = ContentTypes.PACK
            print(f'Parsing {self.content_type} {self.object_id}')
            self.node_id = self.get_node_id()
            self.metadata = PackMetadata(**get_json(self.path / PACK_METADATA_FILENAME))
            self.parse_pack()

    @staticmethod
    def from_database(pack_data: Any) -> 'Pack':
        # todo
        return None

    def add_content_item_node(self, content_item: Any) -> None:
        self.content_items.setdefault(content_item.content_type, []).append(content_item)

    def add_content_item_relationships(self, content_item: Any) -> None:
        content_item.add_relationship(
            Rel.IN_PACK,
            target=self.node_id,
        )
        for k, v in content_item.relationships.items():
            self.relationships.setdefault(k, []).extend(v)

    def parse_pack(self) -> None:
        for folder in ContentTypes.pack_folders(self.path):
            self.parse_pack_folder(folder)

    def parse_pack_folder(self, folder_path: Path) -> None:
        for content_item_path in folder_path.iterdir():  # todo: consider multiprocessing
            if content_item := ContentItemFactory.from_path(content_item_path, self.marketplaces):
                self.add_content_item_node(content_item)
                self.add_content_item_relationships(content_item)
