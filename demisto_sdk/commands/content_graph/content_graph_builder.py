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
        connectors_to_update: Optional[Tuple[str, ...]] = None,
    ) -> None:
        """Imports a content graph from files and updates the given pack and connector nodes.

        Args:
            packs_to_update: Pack ids to refresh. ``None``/empty means "no packs".
            connectors_to_update: Connector directory names (under ``connectors/``)
                to refresh. ``None``/empty means "no connectors".

        At least one of the two must be non-empty for any work to happen -
        otherwise ``_parse_and_model_content`` would fall through to
        ``ContentDTO.from_path(None, None)`` and reparse the entire repo,
        which is both expensive and, when merging an imported graph, would
        duplicate packs that only live in the caller's repo checkout.
        """
        if not packs_to_update and not connectors_to_update:
            return
        self._parse_and_model_content(packs_to_update, connectors_to_update)
        self._create_or_update_graph()

    def init_database(self) -> None:
        self.content_graph.clean_graph()
        self.content_graph.create_indexes_and_constraints()

    def _parse_and_model_content(
        self,
        packs_to_parse: Optional[Tuple[str, ...]] = None,
        connectors_to_parse: Optional[Tuple[str, ...]] = None,
    ) -> None:
        # ``connectors`` is passed as a keyword argument so that existing test
        # mocks of ``_create_content_dto`` that only accept ``(packs)`` keep
        # working unchanged.
        content_dto: ContentDTO = self._create_content_dto(
            packs_to_parse, connectors=connectors_to_parse
        )
        self._collect_nodes_and_relationships_from_model(content_dto)

    def _create_content_dto(
        self,
        packs: Optional[Tuple[str, ...]],
        *,
        connectors: Optional[Tuple[str, ...]] = None,
    ) -> ContentDTO:
        """Parses the repository, then creates and returns a repository model.

        Args:
            packs: A list of pack names to parse. If not provided, parses all packs
                (unless ``connectors`` narrows the parse - see :func:`ContentDTO.from_path`).
            connectors: Keyword-only. A list of connector directory names to
                parse. Made keyword-only so test mocks with the original
                single-positional signature (``mock(packs)``) stay compatible.
        """
        return ContentDTO.from_path(
            packs_to_parse=packs, connectors_to_parse=connectors
        )

    def _collect_nodes_and_relationships_from_model(
        self, content_dto: ContentDTO
    ) -> None:
        for pack in content_dto.packs:
            self.nodes.update(pack.to_nodes())
            self.relationships.update(pack.relationships)
        # Connectors are standalone top-level content items (no enclosing Pack),
        # so we iterate them separately and collect their nodes/relationships
        # the same way we do for packs.
        for connector in content_dto.connectors:
            self.nodes.update(connector.to_nodes())
            self.relationships.update(connector.relationships)

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
