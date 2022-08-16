from datetime import datetime
from packaging.version import Version, parse
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Set

from demisto_sdk.commands.common.tools import get_json
from demisto_sdk.commands.content_graph.constants import (
    ContentTypes,
    Rel,
    PACK_METADATA_FILENAME,
    RelationshipData,
    NodeData
)
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.content_item_factory import ContentItemFactory
import demisto_sdk.commands.content_graph.objects.base_content as base_content


class PackMetadata(BaseModel):
    name: str = ''
    description: str = ''
    created: str = ''
    updated: str = ''
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
    server_min_version: str = ''
    current_version: str = ''
    version_info: int = Field(0, alias='versionInfo')
    tags: List[str] = []
    categories: List[str] = []
    use_cases: List[str] = Field([], alias='useCases')
    keywords: List[str] = []

    class Config:
        arbitrary_types_allowed = True



class Pack(base_content.BaseContent):
    path: Path = ...
    metadata: PackMetadata = None
    content_items: Dict[ContentTypes, List[ContentItem]] = Field({}, alias='contentItems')
    relationships: Dict[Rel, List[RelationshipData]] = Field({}, exclude=True)

    def __init__(self, **data) -> None:
        super().__init__(**data)
        if self.parsing_object:
            self.object_id = self.path.parts[-1]
            self.content_type = ContentTypes.PACK
            print(f'Parsing {self.content_type} {self.object_id}')
            self.node_id = self.get_node_id()
            self.metadata = PackMetadata.parse_file(self.path / PACK_METADATA_FILENAME)
            self.parse_pack()

    @staticmethod
    def from_database(pack_data: NodeData) -> 'Pack':
        metadata = PackMetadata(**pack_data)
        return Pack(metadata=metadata, **pack_data)

    @staticmethod
    def from_repository(path: Path) -> 'Pack':
        return FlatPack(path=path)

    def dict(self, **kwargs) -> Dict[str, Any]:
        if self.parsing_object:
            return 
        return super().dict(**kwargs)

    def add_content_item_node(self, content_item: ContentItem) -> None:
        self.content_items.setdefault(content_item.content_type, []).append(content_item)

    def add_content_item_relationships(self, content_item: ContentItem) -> None:
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

class FlatPack(Pack, PackMetadata):
    def dict(self, **kwargs) -> Dict[str, Any]:
        excluded_keys: List[str] = ['metadata', 'content_items']
        if 'exclude' in kwargs:
            if isinstance(kwargs['exclude'], dict):
                excluded_keys: Dict[str, Any] = {k: True for k in excluded_keys}
                kwargs['exclude'].update(excluded_keys)
            elif isinstance(kwargs['exclude'], set):
                kwargs['exclude'].update(set(excluded_keys))
            else:
                raise Exception('WTF? ' + str(kwargs['exclude']))  # todo
        else:
            kwargs['exclude'] = set(excluded_keys)
        return super().dict(**kwargs)
