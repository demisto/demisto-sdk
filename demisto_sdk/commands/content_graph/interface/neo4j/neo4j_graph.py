import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union, cast
from neo4j import GraphDatabase, Neo4jDriver, Result, Transaction, graph

from itertools import chain

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import (
    NEO4J_DATABASE_URL,
    NEO4J_PASSWORD,
    NEO4J_USERNAME,
    ContentType,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface
from demisto_sdk.commands.content_graph.interface.neo4j.queries.constraints import create_constraints
from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import create_pack_dependencies
from demisto_sdk.commands.content_graph.interface.neo4j.queries.indexes import create_indexes
from demisto_sdk.commands.content_graph.interface.neo4j.queries.nodes import (
    create_nodes,
    delete_all_graph_nodes,
    duplicates_exist,
    match,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.relationships import (
    create_relationships,
    get_connected_nodes_by_relationship_type,
)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent, ServerContent, content_type_to_model
from demisto_sdk.commands.content_graph.objects.integration import BaseCommand
from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData


logger = logging.getLogger("demisto-sdk")


class NoModelException(Exception):
    pass


class Neo4jContentGraphInterface(ContentGraphInterface):

    # this is used to save cache of packs and integrations which queried
    _id_to_obj: Dict[int, Union[BaseContent, BaseCommand]] = {}

    def __init__(
        self,
        start_service: bool = False,
        use_docker: bool = True,
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

    def _serialize_to_obj(self, nodes: Union[dict, Iterable[graph.Node]]) -> None:
        for node in nodes:
            # the dictionary should have the `element_id` field!
            element_id = int(node.element_id)
            if element_id in Neo4jContentGraphInterface._id_to_obj:
                continue
            content_type = node.get("content_type")
            if node.get("not_in_repository"):
                server_content = ServerContent.parse_obj(node)
                Neo4jContentGraphInterface._id_to_obj[element_id] = server_content

            elif content_type == ContentType.COMMAND:
                command = BaseCommand.parse_obj(node)
                Neo4jContentGraphInterface._id_to_obj[element_id] = command

            else:
                model = content_type_to_model.get(content_type)
                if not model:
                    # this currently happens for command node?
                    raise NoModelException(f"No model for {content_type}")
                obj = model.parse_obj(node)
                Neo4jContentGraphInterface._id_to_obj[element_id] = obj

    def _serialize_nodes(self, nodes: Iterable[graph.Node]) -> None:
        nodes = {node for node in nodes if int(node.element_id) not in Neo4jContentGraphInterface._id_to_obj}
        self._serialize_to_obj(nodes)

    def create_indexes_and_constraints(self) -> None:
        with self.driver.session() as session:
            session.execute_write(create_indexes)
            session.execute_write(create_constraints)

    def create_nodes(self, nodes: Dict[ContentType, List[Dict[str, Any]]]) -> None:
        with self.driver.session() as session:
            session.execute_write(create_nodes, nodes)

    def validate_graph(self) -> None:
        with self.driver.session() as session:
            if session.execute_read(duplicates_exist):
                raise Exception("Duplicates found in graph.")

    def create_relationships(self, relationships: Dict[RelationshipType, List[Dict[str, Any]]]) -> None:
        with self.driver.session() as session:
            session.execute_write(create_relationships, relationships)

    def clean_graph(self):
        with self.driver.session() as session:
            session.execute_write(delete_all_graph_nodes)

    def match(
        self,
        marketplace: MarketplaceVersions,
        content_type: Optional[ContentType] = None,
        filter_list: Optional[Iterable[int]] = None,
        is_nested: bool = False,
        **properties,
    ) -> List[BaseContent]:
        with self.driver.session() as session:
            result = session.execute_read(
                match, marketplace, content_type, filter_list, is_nested, **properties
            )
            nodes_set = set()
            integrations_set = set()
            for node_from, rels, nodes_to in result:
                nodes_set.update(set(nodes_to) | {node_from})
                if node_from.get("content_type") == ContentType.PACK:
                    integrations_set.update(
                        {
                            int(node_to.element_id)
                            for node_to in nodes_to
                            if node_to.get("content_type") == ContentType.INTEGRATION
                        }
                    )
            self._serialize_nodes(nodes_set)

            final_result = []
            for node_from, rels, nodes_to in result:
                obj = self._add_relationship(node_from, rels, nodes_to)
                final_result.append(obj)

            if integrations_set:
                self.match(
                    marketplace,
                    ContentType.INTEGRATION,
                    integrations_set,
                )
            return final_result

    def _add_relationship(self, node_from, rels, nodes_to):
        # Command cannot be the start node of relationship
        obj: BaseContent = cast(BaseContent, Neo4jContentGraphInterface._id_to_obj[int(node_from.element_id)])
        rel = [
            RelationshipData(
                relationship_type=rel.type,
                related_to=Neo4jContentGraphInterface._id_to_obj[int(node_to.element_id)],
                is_nested=rel.start_node.element_id != node_from.element_id
                and rel.end_node.element_id != node_from.element_id,
                **rel,
            )
            for node_to, rel in zip(nodes_to, rels)
        ]
        obj.relationshipss.extend(rel)
        return obj

    def create_pack_dependencies(self):
        with self.driver.session() as session:
            session.execute_write(create_pack_dependencies)

    # def get_all_level_dependencies(self, marketplace: MarketplaceVersions) -> Dict[str, Any]:
    #     with self.driver.session() as session:
    #         tx: Transaction = session.begin_transaction()
    #         result = get_all_level_packs_dependencies(tx, marketplace).data()
    #         tx.commit()
    #         tx.close()
    #     return {
    #         row['pack_id']: {
    #             'allLevelDependencies': row['dependencies'],
    #             'fullPath': row['pack_path'],
    #             'path': Path(*Path(row['pack_path']).parts[-2:]).as_posix(),
    #         } for row in result
    #     }

    # def get_first_level_dependencies(self, marketplace: MarketplaceVersions) -> Dict[str, Dict[str, Any]]:
    #     with self.driver.session() as session:
    #         tx: Transaction = session.begin_transaction()
    #         result = get_first_level_dependencies(tx, marketplace).data()
    #         tx.commit()
    #         tx.close()
    #     return {
    #         row['pack_id']: {
    #             dependency['dependency_id']: {
    #                 'mandatory': dependency['mandatory'],
    #                 'display_name': dependency['display_name'],
    #             }
    #             for dependency in row['dependencies']
    #         } for row in result
    #     }

    def get_connected_nodes_by_relationship_type(
        self,
        marketplace: MarketplaceVersions,
        relationship_type: Optional[RelationshipType] = None,
        content_type_from: ContentType = ContentType.BASE_CONTENT,
        content_type_to: ContentType = ContentType.BASE_CONTENT,
        recursive: bool = False,
        **properties,
    ) -> List[BaseContent]:
        with self.driver.session() as session:
            result: List[Tuple[graph.Node, List[graph.Relationship], List[graph.Node]]] = session.execute_read(
                get_connected_nodes_by_relationship_type,
                marketplace,
                relationship_type,
                content_type_from,
                content_type_to,
                recursive,
                **properties,
            )
            nodes_set = set()
            for node_from, rels, nodes_to in result:
                nodes_set.update(nodes_to + [node_from])
            self._serialize_nodes(nodes_set)

            final_result = []
            for node_from, rels, nodes_to in result:
                # Command cannot be the start node of relationship
                obj: BaseContent = cast(BaseContent, Neo4jContentGraphInterface._id_to_obj[int(node_from.element_id)])
                obj.relationshipss.extend(
                    [
                        RelationshipData(
                            relationship_type=rel.type,
                            related_to=Neo4jContentGraphInterface._id_to_obj[int(node_to.element_id)],
                            relationship_data=rel,
                            is_nested=rel.start_node.element_id != node_from.element_id,
                        )
                        for node_to, rel in zip(nodes_to, rels)
                    ]
                )
                final_result.append(obj)
            return final_result

    def run_single_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Result:
        with self.driver.session() as session:
            tx: Transaction = session.begin_transaction()
            result = tx.run(query, parameters)
            tx.commit()
            tx.close()
        return result
