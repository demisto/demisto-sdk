
import pickle

from pathlib import Path
import traceback
from typing import Any, List


from demisto_sdk.commands.content_graph.common import REPO_PATH, Nodes, Relationships
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface

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
    def __init__(self, repo_path: Path, content_graph: ContentGraphInterface, clean_graph: bool = True):
        """ Given a repo path and graph DB interface:
        1. Creates a repository model
        2. Collects all nodes and relationships from the model

        Args:
            repo_path (Path): The repository path.
            content_graph (ContentGraphInterface): The interface to create the graph with.
        """
        self.content_graph = content_graph
        if clean_graph:
            self.content_graph.delete_all_graph_nodes_and_relationships()
        self.nodes: Nodes = Nodes()
        self.relationships: Relationships = Relationships()
        self.repository: Repository = self._create_repository(repo_path)

        for pack in self.repository.packs:
            self.nodes.update(pack.to_nodes())
            self.relationships.update(pack.relationships)

    def _create_repository(self, path: Path) -> Repository:
        """ Parses the repository and creates a repostitory model.

        Args:
            path (Path): The repository path.

        Returns:
            Repository: The repository model.
        """
        repository_parser: RepositoryParser = load_pickle(REPO_PARSER_PKL_PATH.as_posix())
        if not repository_parser:
            try:
                repository_parser = RepositoryParser(path)
                dump_pickle(REPO_PARSER_PKL_PATH.as_posix(), repository_parser)
            except Exception:
                logger.error(traceback.format_exc())
                raise
        return Repository.from_orm(repository_parser)

    def create_graph(self) -> None:
        """ Runs DB queries using the collected nodes and relationships to create the content graph.
        """
        self.content_graph.create_indexes_and_constraints()
        self.content_graph.create_nodes(self.nodes)
        self.content_graph.create_relationships(self.relationships)
        self.content_graph.validate_graph()

    def delete_modified_packs_from_graph(self, packs: List[str]) -> None:
        pass

    def get_modified_packs(self) -> List[str]:
        return []  # todo
