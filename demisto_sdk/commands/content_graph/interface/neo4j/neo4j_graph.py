import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Union, cast

from neo4j import GraphDatabase, Neo4jDriver, Session, graph

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import (NEO4J_DATABASE_URL,
                                                       NEO4J_PASSWORD,
                                                       NEO4J_USERNAME,
                                                       ContentType,
                                                       Neo4jResult,
                                                       RelationshipType)
from demisto_sdk.commands.content_graph.interface.graph import \
    ContentGraphInterface
from demisto_sdk.commands.content_graph.interface.neo4j.queries.constraints import \
    create_constraints
from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import (
    create_pack_dependencies, get_all_level_packs_dependencies)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.indexes import \
    create_indexes
from demisto_sdk.commands.content_graph.interface.neo4j.queries.nodes import (
    _match, create_nodes, delete_all_graph_nodes, duplicates_exist)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.relationships import \
    create_relationships
from demisto_sdk.commands.content_graph.objects.base_content import (
    BaseContent, ServerContent, content_type_to_model)
from demisto_sdk.commands.content_graph.objects.integration import (
    Command, Integration)
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.relationship import \
    RelationshipData

logger = logging.getLogger("demisto-sdk")


class NoModelException(Exception):
    pass


class Neo4jContentGraphInterface(ContentGraphInterface):

    # this is used to save cache of packs and integrations which queried
    _id_to_obj: Dict[int, Union[BaseContent, Command]] = {}

    def __init__(
        self,
        start_service: bool = False,
        use_docker: bool = False,
        output_file: Path = None,
    ) -> None:
        self.driver: Neo4jDriver = GraphDatabase.driver(
            NEO4J_DATABASE_URL,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        )
        if start_service or not neo4j_service.is_alive():
            neo4j_service.start(use_docker)
        self.output_file = output_file
        self.use_docker = use_docker

    def __enter__(self) -> "Neo4jContentGraphInterface":
        return self

    def __exit__(self, *args) -> None:
        if self.output_file:
            neo4j_service.dump(self.output_file, self.use_docker)
            logger.info(f"Dumped graph to file: {self.output_file}")
        self.driver.close()

    def close(self) -> None:
        self.driver.close()

    def _add_to_mapping(self, nodes: Iterable[graph.Node]) -> None:
        """Parses nodes to content objects and adds it to mapping

        Args:
            nodes (Iterable[graph.Node]): List of nodes to parse

        Raises:
            NoModelException: If no model found to parse on
        """
        for node in nodes:
            element_id = node.id
            if element_id in Neo4jContentGraphInterface._id_to_obj:
                continue
            content_type = node.get("content_type")
            if node.get("not_in_repository") or node.get("is_server_item"):
                server_content = ServerContent.parse_obj(node)
                Neo4jContentGraphInterface._id_to_obj[element_id] = server_content

            elif content_type == ContentType.COMMAND:
                command = Command.parse_obj(node)
                Neo4jContentGraphInterface._id_to_obj[element_id] = command

            else:
                model = content_type_to_model.get(content_type)
                if not model:
                    raise NoModelException(f"No model for {content_type}")
                obj = model.parse_obj(node)
                Neo4jContentGraphInterface._id_to_obj[element_id] = obj

    def _add_relationships_to_objects(self, result: List[Neo4jResult]) -> List[Union[BaseContent, Command]]:
        """This adds relationships to given object

        Args:
            result (List[Neo4jResult]): Result from neo4j query

        Returns:
            List[Union[BaseContent, Command]]: The objects to return with relationships
        """
        final_result = []
        for res in result:
            obj = Neo4jContentGraphInterface._id_to_obj[res.node_from.id]
            self._add_relationships(obj, res.relationships, res.nodes_to)
            if isinstance(obj, Pack) and not list(obj.content_items):
                obj.set_content_items()  # type: ignore[union-attr]
            if isinstance(obj, Integration) and not obj.commands:
                obj.set_commands()  # type: ignore[union-attr]

            final_result.append(obj)
        return final_result

    def _get_nodes_set_from_result(
        self, result: List[Neo4jResult], pack_nodes: Set[graph.Node], content_items_nodes: Set[graph.Node]
    ) -> Set[graph.Node]:
        """
        Generate a nodes set of all the nodes in the neo4j result.

        Args:
            result (List[Neo4JResult]): result from noe4j query
            content_items_nodes (Set[graph.Node]): the content items nodes of pack

        Returns:
            Set[graph.Node]): A set of all nodes that returned by query
        """
        nodes_set = set()
        for res in result:
            nodes_set.update(set(res.nodes_to) | {res.node_from})
            if res.node_from.get("content_type") == ContentType.PACK:
                pack_nodes.update({res.node_from.id})
                content_items_nodes.update({int(node_to.id) for _, node_to in zip(res.relationships, res.nodes_to)})

        return nodes_set

    def _add_relationships(
        self,
        obj: Union[BaseContent, Command],
        relationships: List[graph.Relationship],
        nodes_to: List[graph.Node],
    ) -> None:
        """
        Adds relationship to content object

        Args:
            obj (Union[BaseContent, Command]): Object to add relationship to
            node_from (graph.Node): The source node
            relationships (List[graph.Relationship]): The list of relationships from the source
            nodes_to (List[graph.Node]): The list of nodes of the target
        """
        relationships = {
            RelationshipData(
                relationship_type=rel.type,
                source=Neo4jContentGraphInterface._id_to_obj[rel.start_node.id],
                target=Neo4jContentGraphInterface._id_to_obj[rel.end_node.id],
                content_item=Neo4jContentGraphInterface._id_to_obj[node_to.id],
                is_direct=True,
                **rel,
            )
            for node_to, rel in zip(nodes_to, relationships)
        }
        obj.relationships_data.update(relationships)

    def _add_all_level_dependencies(self, session: Session, marketplace: MarketplaceVersions, pack_nodes):
        mandatorily_dependencies: List[Neo4jResult] = session.read_transaction(
            get_all_level_packs_dependencies, marketplace, pack_nodes, True
        )
        content_items_nodes: Set[graph.Node] = set()
        nodes_set = self._get_nodes_set_from_result(mandatorily_dependencies, set(), content_items_nodes)
        self._add_to_mapping(nodes_set)
        if content_items_nodes:
            self.search(
                marketplace,
                filter_list=content_items_nodes,
            )

        for pack in mandatorily_dependencies:
            obj: Pack = cast(Pack, Neo4jContentGraphInterface._id_to_obj[pack.node_from.id])
            for node_to in pack.nodes_to:
                target = Neo4jContentGraphInterface._id_to_obj[node_to.id]
                rel = RelationshipData(
                    RelationshipType.DEPENDS_ON,
                    source=obj,
                    content_item=target,
                    target=target,
                    mandatorily=True,
                    is_direct=False,
                )
                if rel not in obj.relationships_data:
                    obj.relationships_data.add(rel)

    def _search(
        self,
        marketplace: MarketplaceVersions = None,
        content_type: Optional[ContentType] = None,
        filter_list: Optional[Iterable[int]] = None,
        all_level_dependencies: bool = False,
        level: int = 0,
        **properties,
    ) -> List[Union[BaseContent, Command]]:
        """
        This is the implementation for the search function.

        The `level` argument is an extra argument provided to limit the recursion level.
        """
        with self.driver.session() as session:
            result: List[Neo4jResult] = session.read_transaction(
                _match, marketplace, content_type, filter_list, **properties
            )
            content_items_nodes: Set[graph.Node] = set()
            pack_nodes: Set[graph.Node] = set()
            nodes_set = self._get_nodes_set_from_result(result, pack_nodes, content_items_nodes)
            self._add_to_mapping(nodes_set)

            if content_items_nodes and level < 2:
                # limit recursion level is 2, because worst case is `Pack`, and there are two levels until the command
                self._search(
                    marketplace,
                    filter_list=content_items_nodes,
                    level=level + 1,
                )

            final_result = self._add_relationships_to_objects(result)
            if all_level_dependencies and pack_nodes and marketplace:
                self._add_all_level_dependencies(session, marketplace, pack_nodes)
            return final_result

    def create_indexes_and_constraints(self) -> None:
        with self.driver.session() as session:
            session.write_transaction(create_indexes)
            session.write_transaction(create_constraints)

    def create_nodes(self, nodes: Dict[ContentType, List[Dict[str, Any]]]) -> None:
        with self.driver.session() as session:
            session.write_transaction(create_nodes, nodes)

    def validate_graph(self) -> None:
        with self.driver.session() as session:
            if session.read_transaction(duplicates_exist):
                raise Exception("Duplicates found in graph.")

    def create_relationships(self, relationships: Dict[RelationshipType, List[Dict[str, Any]]]) -> None:
        with self.driver.session() as session:
            session.write_transaction(create_relationships, relationships)

    def clean_graph(self):
        with self.driver.session() as session:
            session.write_transaction(delete_all_graph_nodes)
        Neo4jContentGraphInterface._id_to_obj = {}
        super().clean_graph()

    def search(
        self,
        marketplace: MarketplaceVersions = None,
        content_type: Optional[ContentType] = None,
        filter_list: Optional[Iterable[int]] = None,
        all_level_dependencies: bool = False,
        **properties,
    ) -> List[Union[BaseContent, Command]]:
        """
        This searches the database for content items and returns a list of them, including their relationships

        Args:
            marketplace (MarketplaceVersions, optional): Marketplace to search by. Defaults to None.
            content_type (Optional[ContentType], optional): The content_type to filter. Defaults to None.
            filter_list (Optional[Iterable[int]], optional): A list of unique IDs to filter. Defaults to None.
            all_level_dependencies (bool, optional): Whether to return all level dependencies. Defaults to False.
            **properties: A key, value filter for the search. For example: `search(object_id="QRadar")`.

        Returns:
            List[Union[BaseContent, Command]]: The search results
        """
        super().search()
        return self._search(marketplace, content_type, filter_list, all_level_dependencies, 0, **properties)

    def create_pack_dependencies(self):
        with self.driver.session() as session:
            session.write_transaction(create_pack_dependencies)
        super().create_pack_dependencies()

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
