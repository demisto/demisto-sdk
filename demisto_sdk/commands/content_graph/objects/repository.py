import multiprocessing
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any, Dict, Iterator, List, Tuple
from demisto_sdk.commands.content_graph.objects.pack import Pack

from demisto_sdk.commands.content_graph.constants import ContentTypes, NodeData, Rel, RelationshipData, PACKS_FOLDER


# def parse_pack(path: Path) -> Tuple[
#         Dict[ContentTypes, List[NodeData]],
#         Dict[Rel, List[RelationshipData]],
#     ]:
#     nodes: Dict[ContentTypes, List[NodeData]] = {}
#     pack = Pack.from_path(path)
#     for content_type, content_items in pack.content_items.items():
#         nodes[content_type] = [node.dict() for node in content_items]
#     nodes[ContentTypes.PACK] = [pack.dict()]
#     # relationships = [rel.dict() for rel in pack.relationships]
#     return nodes, pack.relationships  # todo: consider pydantic for relationships


class Repository(BaseModel):
    path: Path
    # packs_paths: List[Path] = Field(exclude=True)
    packs: List[Pack]
    # nodes: Dict[ContentTypes, List[NodeData]] = {}
    # relationships: Dict[Rel, List[RelationshipData]] = {}

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
    
    @staticmethod
    def from_path(path: Path) -> 'Repository':
        pool = multiprocessing.Pool(processes=multiprocessing.cpu_count() - 1)
        packs = list(pool.map(Pack.from_path, Repository.iter_packs(path)))
        return Repository(path=path, packs=packs)
    
    @staticmethod
    def iter_packs(path: Path) -> Iterator[Path]:
        packs_folder: Path = path / PACKS_FOLDER
        for path in packs_folder.iterdir():  # todo: handle repo path is invalid
            if path.is_dir() and not path.name.startswith('.'):
                yield path

