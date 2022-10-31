import logging
import traceback
from pathlib import Path
from typing import List

from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.common import Nodes, Relationships
from demisto_sdk.commands.content_graph.interface.graph import \
    ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.parsers.repository import \
    RepositoryParser

json = JSON_Handler()


logger = logging.getLogger("demisto-sdk")


class ContentGraphBuilder:
    def __init__(
        self,
        repo_path: Path,
        content_graph: ContentGraphInterface,
        clean_graph: bool = True,
    ) -> None:
        """Given a repo path and graph DB interface:
        1. Creates a repository model
        2. Collects all nodes and relationships from the model

        Args:
            repo_path (Path): The repository path.
            content_graph (ContentGraphInterface): The interface to create the graph with.
            clean_graph (bool, optional): Whether or not to clean the graph.
        """
        self.content_graph = content_graph
        if clean_graph:
            self.content_graph.clean_graph()
        self.nodes: Nodes = Nodes()
        self.relationships: Relationships = Relationships()
        self.content_dto: ContentDTO = self._create_repository(repo_path)

        for pack in self.content_dto.packs:
            self.nodes.update(pack.to_nodes())
            self.relationships.update(pack.relationships)

    def _create_repository(self, path: Path) -> ContentDTO:
        """Parses the repository and creates a repository model.

        Args:
            path (Path): The repository path.

        Returns:
            Repository: The repository model.
        """
        try:
            repository_parser = RepositoryParser(path)
        except Exception:
            logger.error(traceback.format_exc())
            raise
        return ContentDTO.from_orm(repository_parser)

    def create_graph(self) -> None:
        """Runs DB queries using the collected nodes and relationships to create the content graph."""
        self.content_graph.create_indexes_and_constraints()
        self.content_graph.create_nodes(self.nodes)
        self.content_graph.create_relationships(self.relationships)

    def delete_modified_packs_from_graph(self, packs: List[str]) -> None:
        pass

    def get_modified_packs(self) -> List[str]:
        return []  # todo
