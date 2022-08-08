from abc import ABC, abstractmethod
import multiprocessing

import pickle

from pathlib import Path
from typing import Any, List, Iterator, Dict


from demisto_sdk.commands.content_graph.constants import PACKS_FOLDER, ContentTypes, Rel
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface
from demisto_sdk.commands.content_graph.parsers.pack import PackSubGraphCreator
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.content.content import Content

import logging

REPO_PATH = Path(GitUtil(Content.git()).git_path())
NODES_PKL_PATH = REPO_PATH / 'nodes.pkl'
RELS_PKL_PATH = REPO_PATH / 'rels.pkl'

logger = logging.getLogger('demisto-sdk')


def load_pickle(url: str) -> Any:
    try:
        with open(url, 'rb') as file:
            return pickle.load(file)
    except Exception:
        return {}


def dump_pickle(url: str, data: Any) -> None:
    with open(url, 'wb') as file:
        file.write(pickle.dumps(data))


class ContentGraphBuilder(ABC):
    def __init__(self, repo_path: Path) -> None:
        self.packs_path: Path = repo_path / PACKS_FOLDER
        self.nodes: Dict[ContentTypes, List[Dict[str, Any]]] = load_pickle(NODES_PKL_PATH.as_posix())
        self.relationships: Dict[Rel, List[Dict[str, Any]]] = load_pickle(RELS_PKL_PATH.as_posix())

    @property
    @abstractmethod
    def content_graph(self) -> ContentGraphInterface:
        pass

    def parse_packs(self, packs_paths: Iterator[Path]) -> None:
        """ Parses packs into nodes and relationships by given paths. """
        if self.nodes and self.relationships:
            print('Skipping parsing.')
            return
        pool = multiprocessing.Pool(processes=multiprocessing.cpu_count() - 1)
        for pack_nodes, pack_relationships in pool.map(PackSubGraphCreator.from_path, packs_paths):
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

    def create_graph_from_repository(self) -> None:
        """ Parses all repository packs into nodes and relationships. """
        all_packs_paths = self.iter_packs()
        self.parse_packs(all_packs_paths)
        self.add_parsed_nodes_and_relationships_to_graph()

    def iter_packs(self) -> Iterator[Path]:
        for path in self.packs_path.iterdir():  # todo: handle repo path is invalid
            if path.is_dir() and not path.name.startswith('.'):
                yield path

    def add_parsed_nodes_and_relationships_to_graph(self) -> None:
        dump_pickle(NODES_PKL_PATH.as_posix(), self.nodes)
        dump_pickle(RELS_PKL_PATH.as_posix(), self.relationships)
        self.content_graph.create_indexes_and_constraints()
        self.content_graph.create_nodes(self.nodes)
        self.content_graph.create_relationships(self.relationships)

    def build_modified_packs_paths(self, packs: List[str]) -> Iterator[Path]:
        for pack_id in packs:
            pack_path = Path(self.packs_path / pack_id)
            if not pack_path.is_dir():
                raise Exception(f'Could not find path of pack {pack_id}.')
            yield pack_path

    def parse_modified_packs(self) -> None:
        packs = self.get_modified_packs()
        self.delete_modified_packs_from_graph(packs)
        packs_paths = self.build_modified_packs_paths(packs)
        self.parse_packs(packs_paths)
        self.add_parsed_nodes_and_relationships_to_graph()

    @abstractmethod
    def delete_modified_packs_from_graph(self, packs: List[str]) -> None:
        pass

    def get_modified_packs(self) -> List[str]:
        return []  # todo
