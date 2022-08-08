import logging
import neo4j
from typing import Any, Dict, List, Optional, Tuple

from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface
from demisto_sdk.commands.content_graph.interface.neo4j.queries.indexes import create_indexes
from demisto_sdk.commands.content_graph.interface.neo4j.queries.constraints import create_constraints
from demisto_sdk.commands.content_graph.interface.neo4j.queries.nodes import create_nodes
from demisto_sdk.commands.content_graph.interface.neo4j.queries.relationships import create_relationships
from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import create_pack_dependencies


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

    def create_nodes(self, nodes: Dict[ContentTypes, List[Dict[str, Any]]]) -> None:
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            create_nodes(tx, nodes)
            tx.commit()
            tx.close()

    def create_relationships(self, relationships: Dict[Rel, List[Dict[str, Any]]]) -> None:
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            create_relationships(tx, relationships)
            tx.commit()
            tx.close()

    def create_pack_dependencies(self) -> None:
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            create_pack_dependencies(tx)
            tx.commit()
            tx.close()

    def run_single_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> neo4j.Result:
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            result = tx.run(query, parameters)
            tx.commit()
            tx.close()
        return result
