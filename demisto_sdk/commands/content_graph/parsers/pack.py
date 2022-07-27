import traceback
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .base import BaseContentParser
from demisto_sdk.commands.content_graph.constants import PACK_METADATA_FILENAME, ContentTypes, Rel
from .content_item import ContentItemParser


from demisto_sdk.commands.common.tools import get_json


class PackParser(BaseContentParser):
    def __init__(self, path: Path) -> None:
        self.pack_id: str = path.parts[-1]
        print(f'Parsing {self.content_type} {self.pack_id}')
        self.path: Path = path
        self.metadata: Dict[str, Any] = get_json(path / PACK_METADATA_FILENAME)
        self.marketplaces: List[str] = self.metadata.get('marketplaces', [])

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.PACK

    @property
    def node_id(self) -> str:
        return f'{self.content_type}:{self.pack_id}'

    @property
    def deprecated(self) -> bool:
        return self.metadata.get('deprecated', False)

    def get_data(self) -> Dict[str, Any]:
        return {
            'node_id': self.node_id,
            'id': self.pack_id,
            'name': self.metadata.get('name'),
            'file_path': self.path.as_posix(),
            'current_version': self.metadata.get('currentVersion'),
            'source': ['github.com', 'demisto', 'content'],  # todo
            'author': self.metadata.get('author'),
            'certification': 'certified' if self.metadata.get('support', '').lower() in ['xsoar', 'partner'] else '',
            'tags': self.metadata.get('tags', []),
            'use_cases': self.metadata.get('useCases', []),
            'categories': self.metadata.get('categories', []),
            'deprecated': self.deprecated,
            'marketplaces': self.marketplaces,
        }

    def parse_pack(self) -> None:
        PackSubGraphCreator.add_node(self)
        for folder in ContentTypes.pack_folders(self.path):
            self.parse_pack_folder(folder)

    def parse_pack_folder(self, folder_path: Path) -> None:
        for content_item_path in folder_path.iterdir():
            if content_item := ContentItemParser.from_path(content_item_path, self.marketplaces):
                content_item.connect_to_pack(self.node_id)


class PackSubGraphCreator:
    """ Creates a graph representation of a pack in content repository.

    Attributes:
        nodes:         Holds all parsed nodes of a pack.
        relationships: Holds all parsed relationships of a pack.
    """
    nodes: List[Dict[str, Any]] = []
    relationships: List[Dict[str, Any]] = []

    @staticmethod
    def from_path(path: Path) -> Tuple[List, List]:
        """ Given a pack path, parses it into nodes and relationships. """
        try:
            PackParser(path).parse_pack()
        except Exception:
            print(traceback.format_exc())
            raise Exception(traceback.format_exc())
        return PackSubGraphCreator.nodes, PackSubGraphCreator.relationships

    @staticmethod
    def add_node(parser: BaseContentParser) -> Dict[str, Any]:
        node = {
            'labels': parser.content_type.labels,
            'data': {prop: val for prop, val in parser.get_data().items() if val is not None},
        }
        PackSubGraphCreator.nodes.append(node)

    @staticmethod
    def add_relationship(parser: BaseContentParser, rel_type: Rel, target_node: str, **kwargs: Dict[str, Any]) -> None:
        relationship = {
            'from': parser.node_id,
            'type': rel_type.value,
            'to': target_node,
        }
        if kwargs:
            relationship.update({'props': kwargs})
        PackSubGraphCreator.relationships.append(relationship)
