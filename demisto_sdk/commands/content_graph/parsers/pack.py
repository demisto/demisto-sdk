from pathlib import Path
from typing import Any, Dict, List, Optional

from demisto_sdk.commands.common.tools import get_json
from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel, PACK_METADATA_FILENAME
from demisto_sdk.commands.content_graph.parsers.parser_factory import ParserFactory
from demisto_sdk.commands.content_graph.parsers.base_content import BaseContentParser
from demisto_sdk.commands.content_graph.parsers.content_item import ContentItemParser


class PackMetadataParser:
    def __init__(self, metadata: Dict[str, Any]) -> None:
        self.name: str = metadata['name']
        self.description: str = metadata['description']
        self.created: str = metadata.get('created', '')
        self.updated: str = metadata.get('updated', '')
        self.support: str = metadata['support']
        self.email: str = metadata.get('email', '')
        self.url: str = metadata['url']
        self.author: str = metadata['author']
        self.certification: str = 'certified' if self.support.lower() in ['xsoar', 'partner'] else ''
        self.hidden: bool = metadata.get('hidden', False)
        self.server_min_version: str = metadata.get('serverMinVersion', '')
        self.current_version: str = metadata['currentVersion']
        self.tags: List[str] = metadata['tags']
        self.categories: List[str] = metadata['categories']
        self.use_cases: List[str] = metadata['useCases']
        self.keywords: List[str] = metadata['keywords']
        self.price: Optional[int] = metadata.get('price')
        self.premium: Optional[bool] = metadata.get('premium')
        self.vendor_id: Optional[str] = metadata.get('vendorId')
        self.vendor_name: Optional[str] = metadata.get('vendorName')
        self.preview_only: Optional[bool] = metadata.get('previewOnly')


class PackParser(BaseContentParser, PackMetadataParser):
    def __init__(self, path: Path) -> None:
        metadata: Dict[str, Any] = get_json(path / PACK_METADATA_FILENAME)
        PackMetadataParser.__init__(self, metadata)
        print(f'Parsing {self.content_type} {self.object_id}')
        self.path: Path = path
        self.marketplaces = metadata.get('marketplaces', [])
        self.content_items: Dict[ContentTypes, List[ContentItemParser]] = {}

        self.parse_pack_folders()
    
    @property
    def object_id(self) -> str:
        return self.path.name
    
    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.PACK

    def add_content_item_node(self, parser: ContentItemParser) -> Dict[str, Any]:
        self.content_items.setdefault(parser.content_type, []).append(parser)

    def add_content_item_relationships(self, content_item: ContentItemParser) -> None:
        content_item.add_relationship(
            Rel.IN_PACK,
            target=self.node_id,
        )
        for k, v in content_item.relationships.items():
            self.relationships.setdefault(k, []).extend(v)

    def parse_pack_folders(self) -> None:
        for folder_path in ContentTypes.pack_folders(self.path):
            for content_item_path in folder_path.iterdir():  # todo: consider multiprocessing
                if content_item := ParserFactory.from_path(content_item_path, self.marketplaces):
                    self.add_content_item_node(content_item)
                    content_item.add_relationship(Rel.IN_PACK, target=self.node_id)
