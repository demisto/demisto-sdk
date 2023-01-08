import logging
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from neo4j import GraphDatabase, Neo4jDriver, Session, graph

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.content_graph.common import (
    NEO4J_DATABASE_URL,
    NEO4J_PASSWORD,
    NEO4J_USERNAME,
    ContentType,
    Neo4jRelationshipResult,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface
from demisto_sdk.commands.content_graph.interface.neo4j.import_utils import (
    Neo4jImportHandler,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.constraints import (
    create_constraints,
    drop_constraints,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import (
    create_pack_dependencies,
    get_all_level_packs_dependencies,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.import_export import (
    export_to_csv,
    import_csv,
    merge_duplicate_commands,
    merge_duplicate_content_items,
    post_export_write_queries,
    post_import_write_queries,
    pre_export_write_queries,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.indexes import (
    create_indexes,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.nodes import (
    _match,
    create_nodes,
    delete_all_graph_nodes,
    duplicates_exist,
    remove_empty_properties,
    remove_server_nodes,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.relationships import (
    _match_relationships,
    create_relationships,
)
from demisto_sdk.commands.content_graph.objects.base_content import (
    BaseContent,
    UnknownContent,
    content_type_to_model,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData

logger = logging.getLogger("demisto-sdk")


def _parse_node(element_id: int, node: dict) -> BaseContent:
    """Parses nodes to content objects and adds it to mapping

    Args:
        nodes (Iterable[graph.Node]): List of nodes to parse

    Raises:
        NoModelException: If no model found to parse on
    """
    obj: BaseContent
    content_type = node.get("content_type", "")
    if node.get("not_in_repository"):
        obj = UnknownContent.parse_obj(node)

    else:
        model = content_type_to_model.get(content_type)
        if not model:
            raise NoModelException(f"No model for {content_type}")
        obj = model.parse_obj(node)
    obj.database_id = element_id
    return obj


class NoModelException(Exception):
    pass


class Neo4jContentGraphInterface(ContentGraphInterface):

    # this is used to save cache of packs and integrations which queried
    _id_to_obj: Dict[int, BaseContent] = {}

    def __init__(
        self,
    ) -> None:
        self.driver: Neo4jDriver = GraphDatabase.driver(
            NEO4J_DATABASE_URL,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        )

    def __enter__(self) -> "Neo4jContentGraphInterface":
        if not neo4j_service.is_alive():
            neo4j_service.start()
        return self

    def __exit__(self, *args) -> None:
        self.driver.close()

    def close(self) -> None:
        self.driver.close()

    def _add_relationships_to_objects(
        self,
        session: Session,
        result: Dict[int, Neo4jRelationshipResult],
        marketplace: Optional[MarketplaceVersions],
    ):
        """This adds relationships to given object

        Args:
            session (Session): Neo4j session
            result (List[Neo4jResult]): Result from neo4j query

        Returns:
            List[BaseContent]: The objects to return with relationships
        """
        content_item_nodes: Set[int] = set()
        packs: List[Pack] = []
        nodes_to = []
        for res in result.values():
            nodes_to.extend(res.nodes_to)
        self._add_nodes_to_mapping(nodes_to)
        for id, res in result.items():
            obj = Neo4jContentGraphInterface._id_to_obj[id]
            self._add_relationships(obj, res.relationships, res.nodes_to)
            if isinstance(obj, Pack) and not obj.content_items:
                packs.append(obj)
                content_item_nodes.update(
                    node.id
                    for node, rel in zip(res.nodes_to, res.relationships)
                    if rel.type == RelationshipType.IN_PACK
                )

            if isinstance(obj, Integration) and not obj.commands:
                obj.set_commands()  # type: ignore[union-attr]

        if content_item_nodes:
            content_items_result = session.read_transaction(
                _match_relationships, content_item_nodes, marketplace
            )
            self._add_relationships_to_objects(
                session, content_items_result, marketplace
            )

        # we need to set content items only after they are fully loaded
        for pack in packs:
            pack.set_content_items()

    def _add_relationships(
        self,
        obj: BaseContent,
        relationships: List[graph.Relationship],
        nodes_to: List[graph.Node],
    ) -> None:
        """
        Adds relationship to content object

        Args:
            obj (BaseContent): Object to add relationship to
            node_from (graph.Node): The source node
            relationships (List[graph.Relationship]): The list of relationships from the source
            nodes_to (List[graph.Node]): The list of nodes of the target
        """
        for node_to, rel in zip(nodes_to, relationships):
            obj.add_relationship(
                rel.type,
                RelationshipData(
                    relationship_type=rel.type,
                    source=Neo4jContentGraphInterface._id_to_obj[rel.start_node.id],
                    target=Neo4jContentGraphInterface._id_to_obj[rel.end_node.id],
                    content_item=Neo4jContentGraphInterface._id_to_obj[node_to.id],
                    is_direct=True,
                    **rel,
                ),
            )

    def _add_all_level_dependencies(
        self,
        session: Session,
        marketplace: MarketplaceVersions,
        pack_nodes: Iterable[graph.Node],
    ):
        """Helper method to add all level dependencies

        Args:
            session (Session): neo4j session
            marketplace (MarketplaceVersions): Marketplace version to check for dependencies
            pack_nodes (List[graph.Node]): List of the pack nodes
        """
        mandatorily_dependencies: Dict[
            int, Neo4jRelationshipResult
        ] = session.read_transaction(
            get_all_level_packs_dependencies, pack_nodes, marketplace, True
        )
        nodes_to = []
        for pack_depends_on_relationship in mandatorily_dependencies.values():
            nodes_to.extend(pack_depends_on_relationship.nodes_to)
        self._add_nodes_to_mapping(nodes_to)

        for pack_id, pack_depends_on_relationship in mandatorily_dependencies.items():
            obj = Neo4jContentGraphInterface._id_to_obj[pack_id]
            for node in pack_depends_on_relationship.nodes_to:
                target = Neo4jContentGraphInterface._id_to_obj[node.id]
                obj.add_relationship(
                    RelationshipType.DEPENDS_ON,
                    RelationshipData(
                        relationship_type=RelationshipType.DEPENDS_ON,
                        source=obj,
                        content_item=target,
                        target=target,
                        mandatorily=True,
                        is_direct=False,
                    ),
                )

    def _add_nodes_to_mapping(self, nodes: List[graph.Node]) -> None:
        """Add nodes to the content models mapping

        Args:
            nodes (List[graph.Node]): list of nodes to add
        """
        nodes = filter(lambda node: node.id not in self._id_to_obj, nodes)
        if not nodes:
            logger.debug(
                "No nodes to parse packs because all of them in mapping",
                self._id_to_obj,
            )
            return
        with Pool(processes=cpu_count()) as pool:
            results = pool.starmap(
                _parse_node, ((node.id, dict(node.items())) for node in nodes)
            )
            for result in results:
                assert result.database_id is not None
                self._id_to_obj[result.database_id] = result

    def _search(
        self,
        marketplace: MarketplaceVersions = None,
        content_type: Optional[ContentType] = None,
        ids_list: Optional[Iterable[int]] = None,
        all_level_dependencies: bool = False,
        **properties,
    ) -> List[BaseContent]:
        """
        This is the implementation for the search function.

        """
        with self.driver.session() as session:
            results: List[graph.Node] = session.read_transaction(
                _match, marketplace, content_type, ids_list, **properties
            )
            self._add_nodes_to_mapping(results)

            nodes_without_relationships = {
                result.id
                for result in results
                if not self._id_to_obj[result.id].relationships_data
            }

            relationships: Dict[
                int, Neo4jRelationshipResult
            ] = session.read_transaction(
                _match_relationships, nodes_without_relationships, marketplace
            )
            self._add_relationships_to_objects(session, relationships, marketplace)

            pack_nodes = {
                result.id
                for result in results
                if isinstance(self._id_to_obj[result.id], Pack)
            }
            if all_level_dependencies and pack_nodes and marketplace:
                self._add_all_level_dependencies(session, marketplace, pack_nodes)
            return [self._id_to_obj[result.id] for result in results]

    def create_indexes_and_constraints(self) -> None:
        with self.driver.session() as session:
            session.write_transaction(create_indexes)
            session.write_transaction(create_constraints)

    def create_nodes(self, nodes: Dict[ContentType, List[Dict[str, Any]]]) -> None:
        with self.driver.session() as session:
            session.write_transaction(create_nodes, nodes)
            session.write_transaction(remove_empty_properties)

    def validate_graph(self) -> None:
        with self.driver.session() as session:
            if session.read_transaction(duplicates_exist):
                raise Exception("Duplicates found in graph.")

    def create_relationships(
        self, relationships: Dict[RelationshipType, List[Dict[str, Any]]]
    ) -> None:
        with self.driver.session() as session:
            session.write_transaction(create_relationships, relationships)

    def remove_server_items(self) -> None:
        with self.driver.session() as session:
            session.write_transaction(remove_server_nodes)

    def import_graph(self, imported_path: Optional[Path] = None) -> None:
        """Imports CSV files to neo4j, by:
        1. Dropping the constraints (we temporarily allow creating duplicate nodes from different repos)
        2. Preparing the CSV files for import and importing them
        3. Running serveral DB queries to fix the imported data
        4. Merging duplicate nodes (conmmands/content items)
        5. Recreating the constraints

        Args:
            external_import_paths (List[Path]): A list of external repositories' import paths.
            imported_path (Path): The path to import the graph from.
        """
        import_handler = Neo4jImportHandler(imported_path)
        import_handler.ensure_data_uniqueness()
        node_files = import_handler.get_nodes_files()
        relationship_files = import_handler.get_relationships_files()
        with self.driver.session() as session:
            session.write_transaction(drop_constraints)
            session.write_transaction(import_csv, node_files, relationship_files)
            session.write_transaction(post_import_write_queries)
            session.write_transaction(merge_duplicate_commands)
            session.write_transaction(merge_duplicate_content_items)
            session.write_transaction(create_constraints)
            session.write_transaction(remove_empty_properties)

    def export_graph(self, output_path: Optional[Path] = None) -> None:
        import_handler = Neo4jImportHandler()
        import_handler.clean_import_dir()
        with self.driver.session() as session:
            session.write_transaction(pre_export_write_queries)
            session.write_transaction(export_to_csv, self.repo_path.name)
            session.write_transaction(post_export_write_queries)
        if output_path:
            import_handler.zip_import_dir(output_path)

    def clean_graph(self):
        with self.driver.session() as session:
            session.write_transaction(delete_all_graph_nodes)
        Neo4jContentGraphInterface._id_to_obj = {}
        super().clean_graph()

    def search(
        self,
        marketplace: MarketplaceVersions = None,
        content_type: Optional[ContentType] = None,
        ids_list: Optional[Iterable[int]] = None,
        all_level_dependencies: bool = False,
        **properties,
    ) -> List[BaseContent]:
        """
        This searches the database for content items and returns a list of them, including their relationships

        Args:
            marketplace (MarketplaceVersions, optional): Marketplace to search by. Defaults to None.
            content_type (Optional[ContentType], optional): The content_type to filter. Defaults to None.
            ids_list (Optional[Iterable[int]], optional): A list of unique IDs to filter. Defaults to None.
            all_level_dependencies (bool, optional): Whether to return all level dependencies. Defaults to False.
            **properties: A key, value filter for the search. For example: `search(object_id="QRadar")`.

        Returns:
            List[BaseContent]: The search results
        """
        super().search()
        return self._search(
            marketplace, content_type, ids_list, all_level_dependencies, **properties
        )

    def create_pack_dependencies(self):
        with self.driver.session() as session:
            session.write_transaction(create_pack_dependencies)

    def run_single_query(self, query: str, **kwargs) -> Any:
        with self.driver.session() as session:
            try:
                tx = session.begin_transaction()
                tx.run(tx, query, **kwargs)
                tx.commit()
                tx.close()
            except Exception as e:
                logger.error(f"Error when running query: {e}")
                raise e
