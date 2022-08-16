from repository import Repository

from typing import List, Dict, Any, Tuple
from demisto_sdk.commands.content_graph.constants import ContentTypes, NodeData, Rel, RelationshipData
from pathlib import Path
import multiprocessing
from pack import Pack


class ParseManager:
 
    @staticmethod
    def parse_repo(self, path: Path) -> None:
        repo = Repository.from_path(path)

    def parse_pack(path: Path) -> Tuple[
        Dict[ContentTypes, List[NodeData]],
        Dict[Rel, List[RelationshipData]],
    ]:
    nodes: Dict[ContentTypes, List[NodeData]] = {}
    pack = Pack.from_path(path)
    for content_type, content_items in pack.content_items.items():
        nodes[content_type] = [node.dict() for node in content_items]
    nodes[ContentTypes.PACK] = [pack.dict()]
    # relationships = [rel.dict() for rel in pack.relationships]
    return nodes, pack.relationships  # todo: consider pydantic for relationships


    # def __init__(self, **data) -> None:
    #     super().__init__(**data)
    #     try:
    #         if self.should_parse_repo:
    #             pool = multiprocessing.Pool(processes=multiprocessing.cpu_count() - 1)
    #             for pack_nodes, pack_relationships in pool.map(parse_pack, self.packs_paths):
    #                 self.extend_nodes_and_relationships(pack_nodes, pack_relationships)
    #     except Exception as e:
    #         print(traceback.format_exc())
    #         raise e

    def extend_nodes_and_relationships(
        self,
        pack_nodes: Dict[ContentTypes, List[Dict[str, Any]]],
        pack_relationships: Dict[Rel, List[Dict[str, Any]]],
    ) -> None:
        for content_type, parsed_data in pack_nodes.items():
            self.nodes.setdefault(content_type, []).extend(parsed_data)

        for relationship, parsed_data in pack_relationships.items():
            self.relationships.setdefault(relationship, []).extend(parsed_data)
