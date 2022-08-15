import multiprocessing
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any, Dict, Iterator, List, Tuple
from demisto_sdk.commands.content_graph.objects.pack import Pack

from demisto_sdk.commands.content_graph.constants import ContentTypes, NodeData, Rel, RelationshipData


def parse_pack(path: Path) -> Tuple[List[NodeData], List[RelationshipData]]:
    pack = Pack(path=path)
    nodes = [node.dict() for node in pack.content_items]  # todo: include/exclude
    nodes.append(pack.dict())
    # relationships = [rel.dict() for rel in pack.relationships]
    return nodes, pack.relationships  # todo: consider pydantic for relationships


class Repository(BaseModel):
    packs_paths: Iterator[Path]
    should_parse_repo: bool = True
    nodes: Dict[ContentTypes, List[NodeData]] = Field({}, alias='contentItems')
    relationships: Dict[Rel, List[RelationshipData]] = {}

    def __post_init__(self):
        if self.should_parse_repo:
            pool = multiprocessing.Pool(processes=multiprocessing.cpu_count() - 1)
            for pack_nodes, pack_relationships in pool.map(parse_pack, self.packs_paths):
                self.extend_graph_nodes_and_relationships(pack_nodes, pack_relationships)

    def extend_graph_nodes_and_relationships(
        self,
        pack_nodes: Dict[ContentTypes, List[Dict[str, Any]]],
        pack_relationships: Dict[Rel, List[Dict[str, Any]]],
    ) -> None:
        for content_type, parsed_data in pack_nodes.items():
            self.nodes.setdefault(content_type, []).extend(parsed_data)

        for relationship, parsed_data in pack_relationships.items():
            self.relationships.setdefault(relationship, []).extend(parsed_data)
