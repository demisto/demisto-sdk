import gc
from typing import Optional, Tuple

from demisto_sdk.commands.content_graph.common import Nodes, Relationships
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.repository import (
    ContentDTO,
)

PACKS_PER_BATCH = 600


class ContentGraphBuilder:
    def __init__(self, content_graph: ContentGraphInterface) -> None:
        """Given a graph DB interface:
        1. Creates a repository model
        2. Collects all nodes and relationships from the model

        Args:
            content_graph (ContentGraphInterface): The interface to create the graph with.
        """
        self.content_graph = content_graph
        self.nodes: Nodes = Nodes()
        self.relationships: Relationships = Relationships()

    def update_graph(
        self,
        packs_to_update: Optional[Tuple[str, ...]] = None,
    ) -> None:
        """Imports a content graph from files and updates the given pack nodes.

        Args:
            packs_to_update (Optional[List[str]]): A list of packs to update.
        """
        if not packs_to_update:
            return
        self._parse_and_model_content(packs_to_update)
        self._create_or_update_graph()

    def init_database(self) -> None:
        self.content_graph.clean_graph()
        self.content_graph.create_indexes_and_constraints()

    def _parse_and_model_content(
        self, packs_to_parse: Optional[Tuple[str, ...]] = None
    ) -> None:
        content_dto: ContentDTO = self._create_content_dto(packs_to_parse)
        self._collect_nodes_and_relationships_from_model(content_dto)

    def _create_content_dto(self, packs: Optional[Tuple[str, ...]]) -> ContentDTO:
        """Parses the repository, then creates and returns a repository model.

        Args:
            path (Path): The repository path.
            packs_to_parse (Optional[List[str]]): A list of packs to parse. If not provided, parses all packs.
        """
        return ContentDTO.from_path(packs_to_parse=packs)

    def _collect_nodes_and_relationships_from_model(
        self, content_dto: ContentDTO
    ) -> None:
        for pack in content_dto.packs:
            self.nodes.update(pack.to_nodes())
            self.relationships.update(pack.relationships)

    def create_graph(self) -> None:
        self._parse_and_model_content()
        self._create_or_update_graph()

    def _create_or_update_graph(self) -> None:
        """Runs DB queries using the collected nodes and relationships to create or update the content graph."""
        self.content_graph.create_nodes(self.nodes)
        gc.collect()
        self.content_graph.create_relationships(self.relationships)
        gc.collect()
        self.content_graph.remove_non_repo_items()
