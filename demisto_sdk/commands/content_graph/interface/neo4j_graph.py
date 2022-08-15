from pathlib import Path
import neo4j
from typing import Any, Dict, List, Optional, Tuple
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface
from demisto_sdk.commands.content_graph.interface.neo4j.queries.indexes import create_indexes
from demisto_sdk.commands.content_graph.interface.neo4j.queries.constraints import create_constraints
from demisto_sdk.commands.content_graph.interface.neo4j.queries.nodes import create_nodes
from demisto_sdk.commands.content_graph.interface.neo4j.queries.relationships import create_relationships
from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import create_pack_dependencies, get_first_level_dependencies, get_packs_dependencies


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
    
    def get_all_level_dependencies(self, marketplace: MarketplaceVersions) -> Dict[str, Any]:
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            result = get_packs_dependencies(tx, marketplace).data()
            tx.commit()
            tx.close()
        return {
            row['pack_id']: {
                'allLevelDependencies': row['dependencies'],
                'fullPath': row['pack_path'],
                'path': Path(*Path(row['pack_path']).parts[-2:]).as_posix(),
            } for row in result
        }
    
    def get_first_level_dependencies(self, marketplace: MarketplaceVersions) -> Dict[str, Dict[str, Any]]:
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            result = get_first_level_dependencies(tx, marketplace).data()
            tx.commit()
            tx.close()
        return {
            row['pack_id']: {
                dependency['dependency_id']: {
                    'mandatory': dependency['mandatory'],
                    'display_name': dependency['display_name'],
                }
                for dependency in row['dependencies']
            } for row in result
        }

    def run_single_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> neo4j.Result:
        with self.driver.session() as session:
            tx: neo4j.Transaction = session.begin_transaction()
            result = tx.run(query, parameters)
            tx.commit()
            tx.close()
        return result
