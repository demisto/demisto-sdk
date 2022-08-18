
import pickle

from pathlib import Path
import traceback
from typing import Any, List, Dict


from demisto_sdk.commands.content_graph.constants import ContentTypes, NodeData, Rel, RelationshipData, REPO_PATH
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.content.content import Content
from .objects.content_item import ContentItem

from demisto_sdk.commands.content_graph.objects.repository import Repository
from demisto_sdk.commands.content_graph.parsers.repository import RepositoryParser

from demisto_sdk.commands.common.handlers import JSON_Handler

import logging

json = JSON_Handler()


REPO_PARSER_PKL_PATH = REPO_PATH / 'repo_parser.pkl'

logger = logging.getLogger('demisto-sdk')


def load_pickle(url: str) -> Any:
    try:
        with open(url, 'rb') as file:
            return pickle.load(file)
    except Exception:
        return None


def dump_pickle(url: str, data: Any) -> None:
    with open(url, 'wb') as file:
        file.write(pickle.dumps(data))


class ContentGraphBuilder:
    def __init__(self, repo_path: Path, content_graph: ContentGraphInterface):
        self.content_graph = content_graph
        self.nodes: Dict[ContentTypes, List[NodeData]] = {}
        self.relationships: Dict[Rel, List[RelationshipData]] = {}
        self.repository: Repository = self._parse_repo(repo_path)
        for pack in self.repository.packs:
            self._extend_nodes_and_relationships(pack.content_items, pack.relationships)

    def _parse_repo(self, path: Path) -> Repository:
        repository_parser: RepositoryParser = load_pickle(REPO_PARSER_PKL_PATH.as_posix())
        if not repository_parser:
            try:
                repository_parser = RepositoryParser(path)
                dump_pickle(REPO_PARSER_PKL_PATH.as_posix(), repository_parser)
            except Exception:
                print(traceback.format_exc())
                raise
        return Repository.from_orm(repository_parser)

    def _extend_nodes_and_relationships(
        self,
        pack_content_items: Dict[ContentTypes, List[ContentItem]],
        pack_relationships: Dict[Rel, List[RelationshipData]],
    ) -> None:
        for content_type, content_items in pack_content_items.items():
            pack_nodes = [json.loads(content_item.json()) for content_item in content_items]  # TODO do we really need to convert to dict?
            self.nodes.setdefault(content_type, []).extend(pack_nodes)

        for relationship, parsed_data in pack_relationships.items():
            self.relationships.setdefault(relationship, []).extend(parsed_data)

    def create_graph(self) -> None:
        self.content_graph.create_indexes_and_constraints()
        self.content_graph.create_nodes(self.nodes)
        self.content_graph.create_relationships(self.relationships)
        self.content_graph.validate_graph()

    # def build_modified_packs_paths(self, packs: List[str]) -> Iterator[Path]:
    #     for pack_id in packs:
    #         pack_path = Path(self.packs_path / pack_id)
    #         if not pack_path.is_dir():
    #             raise Exception(f'Could not find path of pack {pack_id}.')
    #         yield pack_path

    # def parse_modified_packs(self) -> None:
    #     packs = self.get_modified_packs()
    #     self.delete_modified_packs_from_graph(packs)
    #     packs_paths = self.build_modified_packs_paths(packs)
    #     self.parse_packs(packs_paths)
    #     self.create_graph()

    def delete_modified_packs_from_graph(self, packs: List[str]) -> None:
        pass

    def get_modified_packs(self) -> List[str]:
        return []  # todo
