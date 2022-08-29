from pathlib import Path
import neo4j
from typing import Any, Dict, List, Optional, Tuple
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.common import ContentType, Relationship
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface
from demisto_sdk.commands.content_graph.interface.neo4j.queries.indexes import create_indexes
from demisto_sdk.commands.content_graph.interface.neo4j.queries.constraints import create_constraints
from demisto_sdk.commands.content_graph.interface.neo4j.queries.nodes import (
    create_nodes,
    duplicates_exist,
    get_packs_content_items,
    get_all_integrations_with_commands,
    delete_all_graph_nodes,
    get_nodes_by_type,
    search_nodes,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.relationships import (
    create_relationships,
    get_relationships_by_type,
)


class Neo4jContentGraphInterface(ContentGraphInterface):
    def __init__(self, database_uri, auth: Tuple[str, str]) -> None:
        self.driver: neo4j.Neo4jDriver = neo4j.GraphDatabase.driver(database_uri, auth=auth)
    
    def create_indexes_and_constraints(self) -> None:
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            create_indexes(tx)
            create_constraints(tx)
            tx.commit()
            tx.close()

    def create_nodes(self, nodes: Dict[ContentType, List[Dict[str, Any]]]) -> None:
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            create_nodes(tx, nodes)
            tx.commit()
            tx.close()
    
    def validate_graph(self) -> None:
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            if duplicates_exist(tx):
                raise Exception('Duplicates found in graph.')
            tx.close()

    def create_relationships(self, relationships: Dict[Relationship, List[Dict[str, Any]]]) -> None:
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            create_relationships(tx, relationships)
            tx.commit()
            tx.close()

    def get_packs_content_items(self, marketplace: MarketplaceVersions):
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            result = get_packs_content_items(tx, marketplace)
            tx.close()
        return result
    
    def get_all_integrations_with_commands(self):
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            result = get_all_integrations_with_commands(tx)
            tx.close()
        return result

    def clean_graph(self):
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            delete_all_graph_nodes(tx)
            tx.commit()
            tx.close()

    def get_nodes_by_type(self, content_type: ContentType) -> Any:
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            result = get_nodes_by_type(tx, content_type)
            tx.close()
        return result

    def search_nodes(
        self,
        content_type: Optional[ContentType] = None,
        **properties
    ) -> Any:
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            result = search_nodes(tx, content_type, **properties)
            tx.close()
        return result

    def get_single_node(
        self,
        content_type: Optional[ContentType] = None,
        **properties
    ) -> Any:
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            result = search_nodes(tx, content_type, single_result=True, **properties)
            tx.close()
        return result

    def get_relationships_by_type(self, relationship: Relationship) -> Any:
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            result = get_relationships_by_type(tx, relationship)
            tx.close()
        return result

    def run_single_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> neo4j.Result:
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            result = tx.run(query, parameters)
            tx.commit()
            tx.close()
        return result
    
    
