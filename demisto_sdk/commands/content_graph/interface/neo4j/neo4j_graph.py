import os
from multiprocessing import Pool
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

from neo4j import Driver, GraphDatabase, Session, graph

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import download_content_graph
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
    get_all_level_packs_relationships,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.import_export import (
    export_graphml,
    import_graphml,
    merge_duplicate_commands,
    merge_duplicate_content_items,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.indexes import (
    create_indexes,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.nodes import (
    _match,
    create_nodes,
    delete_all_graph_nodes,
    get_relationships_to_preserve,
    get_schema,
    remove_content_private_nodes,
    remove_empty_properties,
    remove_packs_before_creation,
    remove_server_nodes,
    return_preserved_relationships,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.relationships import (
    _match_relationships,
    create_relationships,
    get_sources_by_path,
    get_targets_by_path,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.validations import (
    get_items_using_deprecated,
    validate_core_packs_dependencies,
    validate_duplicate_ids,
    validate_fromversion,
    validate_hidden_pack_dependencies,
    validate_marketplaces,
    validate_multiple_packs_with_same_display_name,
    validate_multiple_script_with_same_name,
    validate_toversion,
    validate_unknown_content,
)
from demisto_sdk.commands.content_graph.objects.base_content import (
    CONTENT_TYPE_TO_MODEL,
    BaseNode,
    UnknownContent,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData


def _parse_node(element_id: str, node: dict) -> BaseNode:
    """Parses nodes to content objects and adds it to mapping

    Args:
        nodes (Iterable[graph.Node]): List of nodes to parse

    Raises:
        NoModelException: If no model found to parse on
    """
    obj: BaseNode
    content_type = node.get("content_type", "")
    if node.get("not_in_repository"):
        obj = UnknownContent.parse_obj(node)

    else:
        model = CONTENT_TYPE_TO_MODEL.get(content_type)
        if not model:
            raise NoModelException(f"No model for {content_type}")
        obj = model.parse_obj(node)
    obj.database_id = element_id
    return obj


class NoModelException(Exception):
    pass


class Neo4jContentGraphInterface(ContentGraphInterface):
    def __init__(
        self,
    ) -> None:
        self._import_handler = Neo4jImportHandler()
        self._id_to_obj: Dict[str, BaseNode] = {}

        if not self.is_alive():
            neo4j_service.start()
        self._rels_to_preserve: List[Dict[str, Any]] = []  # used for graph updates

        self._init_driver()
        self.output_path = None
        if artifacts_folder := os.getenv("ARTIFACTS_FOLDER"):
            self.output_path = Path(artifacts_folder) / "content_graph"
            self.output_path.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> "Neo4jContentGraphInterface":
        return self

    def __exit__(self, *args) -> None:
        self.driver.close()

    def _init_driver(self):
        self.driver: Driver = GraphDatabase.driver(
            NEO4J_DATABASE_URL,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        )

    @property
    def import_path(self) -> Path:
        return self._import_handler.import_path

    def clean_import_dir(self) -> None:
        return self._import_handler.clean_import_dir()

    def move_to_import_dir(self, imported_path: Path) -> None:
        return self._import_handler.extract_files_from_path(imported_path)

    def close(self) -> None:
        self.driver.close()

    def _add_relationships_to_objects(
        self,
        session: Session,
        result: Dict[str, Neo4jRelationshipResult],
        marketplace: Optional[MarketplaceVersions] = None,
    ):
        """This adds relationships to given object

        Args:
            session (Session): Neo4j session
            result (List[Neo4jResult]): Result from neo4j query

        Returns:
            List[BaseNode]: The objects to return with relationships
        """
        content_item_nodes: Set[str] = set()
        packs: List[Pack] = []
        nodes_to = []
        for res in result.values():
            nodes_to.extend(res.nodes_to)
        self._add_nodes_to_mapping(nodes_to)
        for id, res in result.items():
            obj = self._id_to_obj[id]
            self._add_relationships(obj, res.relationships, res.nodes_to)
            if isinstance(obj, Pack) and not obj.content_items:
                packs.append(obj)
                content_item_nodes.update(
                    node.element_id
                    for node, rel in zip(res.nodes_to, res.relationships)
                    if rel.type == RelationshipType.IN_PACK
                )

            if isinstance(obj, Integration) and not obj.commands:
                obj.set_commands()  # type: ignore[union-attr]

        if content_item_nodes:
            content_items_result = session.execute_read(
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
        obj: BaseNode,
        relationships: List[graph.Relationship],
        nodes_to: List[graph.Node],
    ) -> None:
        """
        Adds relationship to content object

        Args:
            obj (BaseNode): Object to add relationship to
            node_from (graph.Node): The source node
            relationships (List[graph.Relationship]): The list of relationships from the source
            nodes_to (List[graph.Node]): The list of nodes of the target
        """
        for node_to, rel in zip(nodes_to, relationships):
            if not rel.start_node or not rel.end_node:
                raise ValueError("Relationships must have start and end nodes")
            obj.add_relationship(
                RelationshipType(rel.type),
                RelationshipData(
                    relationship_type=rel.type,
                    source_id=rel.start_node.element_id,
                    target_id=rel.end_node.element_id,
                    content_item_to=self._id_to_obj[node_to.element_id],
                    is_direct=True,
                    **rel,
                ),
            )

    def _add_all_level_relationships(
        self,
        session: Session,
        node_ids: Iterable[str],
        relationship_type: RelationshipType,
        marketplace: MarketplaceVersions = None,
    ):
        """Helper method to add all level dependencies

        Args:
            session (Session): neo4j session
            marketplace (MarketplaceVersions): Marketplace version to check for dependencies
            pack_nodes (List[graph.Node]): List of the pack nodes
        """
        relationships: Dict[str, Neo4jRelationshipResult] = session.execute_read(
            get_all_level_packs_relationships,
            relationship_type,
            node_ids,
            marketplace,
            True,
        )
        nodes_to = []
        for content_item_relationship in relationships.values():
            nodes_to.extend(content_item_relationship.nodes_to)
        self._add_nodes_to_mapping(nodes_to)

        for content_item_id, content_item_relationship in relationships.items():
            obj = self._id_to_obj[content_item_id]
            for node in content_item_relationship.nodes_to:
                target = self._id_to_obj[node.element_id]
                source_id = content_item_id
                target_id = node.element_id
                if relationship_type == RelationshipType.IMPORTS:
                    # the import relationship is from the integration to the content item
                    source_id = node.element_id
                    target_id = content_item_id
                obj.add_relationship(
                    relationship_type,
                    RelationshipData(
                        relationship_type=relationship_type,
                        source_id=source_id,
                        target_id=target_id,
                        content_item_to=target,
                        mandatorily=True,
                        is_direct=False,
                    ),
                )

    def _add_nodes_to_mapping(self, nodes: Iterable[graph.Node]) -> None:
        """Add nodes to the content models mapping

        Args:
            nodes (List[graph.Node]): list of nodes to add
        """
        nodes = filter(lambda node: node.element_id not in self._id_to_obj, nodes)
        if not nodes:
            logger.debug(
                "No nodes to parse packs because all of them in mapping",
                self._id_to_obj,
            )
            return
        with Pool(processes=cpu_count()) as pool:
            results = pool.starmap(
                _parse_node, ((node.element_id, dict(node.items())) for node in nodes)
            )
            for result in results:
                assert result.database_id is not None
                self._id_to_obj[result.database_id] = result

    def _search(
        self,
        marketplace: MarketplaceVersions = None,
        content_type: ContentType = ContentType.BASE_NODE,
        ids_list: Optional[Iterable[int]] = None,
        all_level_dependencies: bool = False,
        all_level_imports: bool = False,
        **properties,
    ) -> List[BaseNode]:
        """
        This is the implementation for the search function.

        """
        with self.driver.session() as session:
            results: List[graph.Node] = session.execute_read(
                _match, marketplace, content_type, ids_list, **properties
            )
            self._add_nodes_to_mapping(results)

            nodes_without_relationships = {
                result.element_id
                for result in results
                if not self._id_to_obj[result.element_id].relationships_data
            }

            relationships: Dict[str, Neo4jRelationshipResult] = session.execute_read(
                _match_relationships, nodes_without_relationships, marketplace
            )
            self._add_relationships_to_objects(session, relationships, marketplace)

            pack_nodes = {
                result.element_id
                for result in results
                if isinstance(self._id_to_obj[result.element_id], Pack)
            }
            nodes = {result.element_id for result in results}
            if all_level_imports:
                self._add_all_level_relationships(
                    session, nodes, RelationshipType.IMPORTS
                )
            if all_level_dependencies and pack_nodes and marketplace:
                self._add_all_level_relationships(
                    session, pack_nodes, RelationshipType.DEPENDS_ON, marketplace
                )
            return [self._id_to_obj[result.element_id] for result in results]

    def create_indexes_and_constraints(self) -> None:
        logger.debug("Creating graph indexes and constraints...")
        with self.driver.session() as session:
            session.execute_write(create_indexes)
            session.execute_write(create_constraints)

    def create_nodes(self, nodes: Dict[ContentType, List[Dict[str, Any]]]) -> None:
        logger.info("Creating graph nodes...")
        pack_ids = [p.get("object_id") for p in nodes.get(ContentType.PACK, [])]
        with self.driver.session() as session:
            self._rels_to_preserve = session.execute_read(
                get_relationships_to_preserve, pack_ids
            )
            session.execute_write(remove_packs_before_creation, pack_ids)
            session.execute_write(create_nodes, nodes)
            session.execute_write(remove_empty_properties)

    def get_relationships_by_path(
        self,
        path: Path,
        relationship_type: RelationshipType,
        content_type: ContentType,
        depth: int,
        marketplace: MarketplaceVersions,
        retrieve_sources: bool,
        retrieve_targets: bool,
        mandatory_only: bool,
        include_tests: bool,
        include_deprecated: bool,
        include_hidden: bool,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        with self.driver.session() as session:
            sources = (
                session.execute_read(
                    get_sources_by_path,
                    path,
                    relationship_type,
                    content_type,
                    depth,
                    marketplace,
                    mandatory_only,
                    include_tests,
                    include_deprecated,
                    include_hidden,
                )
                if retrieve_sources
                else []
            )
            targets = (
                session.execute_read(
                    get_targets_by_path,
                    path,
                    relationship_type,
                    content_type,
                    depth,
                    marketplace,
                    mandatory_only,
                    include_tests,
                    include_deprecated,
                    include_hidden,
                )
                if retrieve_targets
                else []
            )
            return sources, targets

    def get_unknown_content_uses(
        self, file_paths: List[str], raises_error: bool, include_optional: bool = False
    ) -> List[BaseNode]:
        with self.driver.session() as session:
            results: Dict[str, Neo4jRelationshipResult] = session.execute_read(
                validate_unknown_content, file_paths, raises_error, include_optional
            )
            self._add_nodes_to_mapping(result.node_from for result in results.values())
            self._add_relationships_to_objects(session, results)
            return [self._id_to_obj[result] for result in results]

    def get_duplicate_pack_display_name(
        self, file_paths: List[str]
    ) -> List[Tuple[str, List[str]]]:
        with self.driver.session() as session:
            results = session.execute_read(
                validate_multiple_packs_with_same_display_name, file_paths
            )
            return results

    def get_duplicate_script_name_included_incident(
        self, file_paths: List[str]
    ) -> Dict[str, str]:
        with self.driver.session() as session:
            return session.execute_read(
                validate_multiple_script_with_same_name, file_paths
            )

    def validate_duplicate_ids(
        self, file_paths: List[str]
    ) -> List[Tuple[BaseNode, List[BaseNode]]]:
        with self.driver.session() as session:
            duplicates = session.execute_read(validate_duplicate_ids, file_paths)
        all_nodes = []
        for content_item, dups in duplicates:
            all_nodes.append(content_item)
            all_nodes.extend(dups)
        self._add_nodes_to_mapping(all_nodes)
        duplicate_models = []
        for content_item, dups in duplicates:
            dups = [self._id_to_obj[duplicate.element_id] for duplicate in dups]
            duplicate_models.append((self._id_to_obj[content_item.element_id], dups))
        return duplicate_models

    def find_uses_paths_with_invalid_fromversion(
        self, file_paths: List[str], for_supported_versions=False
    ) -> List[BaseNode]:
        """Searches and retrievs content items who use content items with a lower fromvesion.

        Args:
            file_paths (List[str]): A list of content items' paths to check.
                If not given, runs the query over all content items.

        Returns:
            List[BaseNode]: The content items who use content items with a lower fromvesion.
        """
        with self.driver.session() as session:
            results: Dict[str, Neo4jRelationshipResult] = session.execute_read(
                validate_fromversion, file_paths, for_supported_versions
            )
            self._add_nodes_to_mapping(result.node_from for result in results.values())
            self._add_relationships_to_objects(session, results)
            return [self._id_to_obj[result] for result in results]

    def find_uses_paths_with_invalid_toversion(
        self, file_paths: List[str], for_supported_versions=False
    ) -> List[BaseNode]:
        """Searches and retrievs content items who use content items with a higher toversion.

        Args:
            file_paths (List[str]): A list of content items' paths to check.
                If not given, runs the query over all content items.

        Returns:
            List[BaseNode]: The content items who use content items with a higher toversion.
        """
        with self.driver.session() as session:
            results: Dict[str, Neo4jRelationshipResult] = session.execute_read(
                validate_toversion, file_paths, for_supported_versions
            )
            self._add_nodes_to_mapping(result.node_from for result in results.values())
            self._add_relationships_to_objects(session, results)
            return [self._id_to_obj[result] for result in results]

    def find_items_using_deprecated_items(self, file_paths: List[str]) -> List[dict]:
        """Searches for content items who use content items which are deprecated.

        Args:
            file_paths (List[str]): A list of content items' paths to check.
                If not given, runs the query over all content items.
        Returns:
            List[dict]: A list of dicts with the deprecated item and all the items used it.
        """
        with self.driver.session() as session:
            return session.execute_read(get_items_using_deprecated, file_paths)

    def find_uses_paths_with_invalid_marketplaces(
        self, pack_ids: List[str]
    ) -> List[BaseNode]:
        """Searches and retrievs content items who use content items with invalid marketplaces.

        Args:
            file_paths (List[str]): A list of content items' paths to check.
                If not given, runs the query over all content items.

        Returns:
            List[BaseNode]: The content items who use content items with invalid marketplaces.
        """
        with self.driver.session() as session:
            results: Dict[str, Neo4jRelationshipResult] = session.execute_read(
                validate_marketplaces, pack_ids
            )
            self._add_nodes_to_mapping(result.node_from for result in results.values())
            self._add_relationships_to_objects(session, results)
            return [self._id_to_obj[result] for result in results]

    def find_core_packs_depend_on_non_core_packs(
        self,
        pack_ids: List[str],
        marketplace: MarketplaceVersions,
        core_pack_list: List[str],
    ) -> List[BaseNode]:
        """Searches and retrieves core packs who depends on content items who are not core packs.

        Args:
            pack_ids (List[str]): A list of content items pack_ids to check.
            core_pack_list: A list of core packs

        Returns:
            List[BaseNode]: The core packs who depends on content items who are not core packs.
        """
        with self.driver.session() as session:
            results: Dict[str, Neo4jRelationshipResult] = session.execute_read(
                validate_core_packs_dependencies, pack_ids, marketplace, core_pack_list
            )
            self._add_nodes_to_mapping(result.node_from for result in results.values())
            self._add_relationships_to_objects(session, results)
            return [self._id_to_obj[result] for result in results]

    def find_mandatory_hidden_packs_dependencies(
        self, pack_ids: List[str]
    ) -> List[BaseNode]:
        """
        Retrieves all the packs that are dependent on hidden packs

        Args:
            pack_ids (List[str]): A list of content items pack_ids to check.

        Returns:
            List[BaseNode]: Packs which depend on hidden packs in case exist.

        """
        with self.driver.session() as session:
            results = session.execute_read(validate_hidden_pack_dependencies, pack_ids)
            self._add_nodes_to_mapping(result.node_from for result in results.values())
            self._add_relationships_to_objects(session, results)
            return [self._id_to_obj[result] for result in results]

    def create_relationships(
        self, relationships: Dict[RelationshipType, List[Dict[str, Any]]]
    ) -> None:
        logger.info("Creating graph relationships...")
        with self.driver.session() as session:
            session.execute_write(create_relationships, relationships, timeout=120)
            if self._rels_to_preserve:
                session.execute_write(
                    return_preserved_relationships, self._rels_to_preserve
                )

    def remove_non_repo_items(self) -> None:
        with self.driver.session() as session:
            # Removing content-private nodes should be a temporary workaround.
            # For more details: https://jira-hq.paloaltonetworks.local/browse/CIAC-7149
            session.execute_write(remove_content_private_nodes)
            session.execute_write(remove_server_nodes)

    def import_graph(
        self,
        imported_path: Optional[Path] = None,
        download: bool = False,
        fail_on_error: bool = False,
    ) -> bool:
        """Imports GraphML files to neo4j, by:
        1. Preparing the GraphML files for import
        2. Dropping the constraints (we temporarily allow creating duplicate nodes from different repos)
        3. Import the GraphML files
        4. Merging duplicate nodes (conmmands/content items)
        5. Recreating the constraints
        6. Remove empty properties

        Args:
            external_import_paths (List[Path]): A list of external repositories' import paths.
            imported_path (Path): The path to import the graph from.
            download (bool): Wheter download the graph from bucket or not.
            fail_on_error (bool): Whether to raise exception on error or not.

        Returns:
            bool: Whether the import was successful or not
        """
        if imported_path:
            logger.info(f"Importing graph from {imported_path}")
            self.clean_import_dir()

        if download:
            logger.info("Importing graph from bucket")
            self.clean_import_dir()
            try:
                with NamedTemporaryFile() as temp_file:
                    official_content_graph = download_content_graph(
                        Path(temp_file.name),
                    )
                    self.move_to_import_dir(official_content_graph)
            except Exception:
                logger.error("Failed to download content graph from bucket")
                if fail_on_error:
                    raise
                return False

        logger.info("Importing graph from GraphML files...")
        self._import_handler.extract_files_from_path(imported_path)
        self._import_handler.ensure_data_uniqueness()
        graphml_filenames = self._import_handler.get_graphml_filenames()
        if not graphml_filenames:
            # no ml files found in the import dir, nothing to import
            return False
        with self.driver.session() as session:
            session.execute_write(drop_constraints)
            session.execute_write(import_graphml, graphml_filenames)
            session.execute_write(merge_duplicate_commands)
            session.execute_write(create_constraints)
            if len(graphml_filenames) > 1:
                session.execute_write(merge_duplicate_content_items)
        has_infra_graph_been_changed = self._has_infra_graph_been_changed()
        self._id_to_obj = {}
        return not has_infra_graph_been_changed

    def export_graph(
        self,
        output_path: Optional[Path] = None,
        override_commit: bool = True,
        marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        clean_import_dir: bool = True,
    ) -> None:
        if clean_import_dir:
            self.clean_import_dir()
        with self.driver.session() as session:
            session.execute_write(export_graphml, self.repo_path.name)
        self.dump_metadata(override_commit)
        self.dump_depends_on()
        if output_path:
            output_path = output_path / marketplace.value
            logger.info(f"Saving content graph in {output_path}.zip")
            self.zip_import_dir(output_path)

    def clean_graph(self):
        with self.driver.session() as session:
            session.execute_write(delete_all_graph_nodes)
        self._id_to_obj = {}
        super().clean_graph()

    def search(
        self,
        marketplace: Union[MarketplaceVersions, str] = None,
        content_type: ContentType = ContentType.BASE_NODE,
        ids_list: Optional[Iterable[int]] = None,
        all_level_dependencies: bool = False,
        all_level_imports: bool = False,
        **properties,
    ) -> List[BaseNode]:
        """
        This searches the database for content items and returns a list of them, including their relationships

        Args:
            marketplace (MarketplaceVersions, optional): Marketplace to search by. Defaults to None.
            content_type (ContentType): The content_type to filter. Defaults to ContentType.BASE_NODE.
            ids_list (Optional[Iterable[int]], optional): A list of unique IDs to filter. Defaults to None.
            all_level_dependencies (bool, optional): Whether to return all level dependencies. Defaults to False.
            **properties: A key, value filter for the search. For example: `search(object_id="QRadar")`.

        Returns:
            List[BaseNode]: The search results
        """
        if isinstance(marketplace, str):
            marketplace = MarketplaceVersions(marketplace)

        super().search()
        return self._search(
            marketplace,
            content_type,
            ids_list,
            all_level_dependencies,
            all_level_imports,
            **properties,
        )

    def create_pack_dependencies(self):
        logger.info("Creating pack dependencies...")
        with self.driver.session() as session:
            self._depends_on = session.execute_write(create_pack_dependencies)

    def is_alive(self):
        return neo4j_service.is_alive()

    def get_schema(self) -> dict:
        with self.driver.session() as session:
            return session.execute_read(get_schema)

    def run_single_query(self, query: str, **kwargs) -> Any:
        with self.driver.session() as session:
            try:
                tx = session.begin_transaction()
                res = tx.run(query, **kwargs)
                data = res.data()
                tx.commit()
                tx.close()
                return data
            except Exception as e:
                logger.error(f"Error when running query: {e}")
                raise e
