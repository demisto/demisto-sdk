from neo4j import Transaction, Result
from typing import List

from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel


NODE_PROPERTY_UNIQUENESS_TEMPLATE = 'CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE'
NODE_PROPERTY_EXISTENCE_TEMPLATE = 'CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS NOT NULL'
REL_PROPERTY_EXISTENCE_TEMPLATE = 'CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:{label}]-() REQUIRE r.{prop} IS NOT NULL'


def create_constraints(tx: Transaction) -> List[Result]:
    results: List[Result] = []
    results.extend(create_nodes_constraints(tx))
    # results.append(create_relationships_constraints(tx))
    return results


def create_nodes_constraints(tx: Transaction) -> List[Result]:
    results: List[Result] = []
    results.append(create_node_property_uniqueness_constraint(tx, ContentTypes.COMMAND, 'id'))
    results.append(create_node_property_uniqueness_constraint(tx, ContentTypes.COMMAND, 'node_id'))
    return results


def create_node_property_uniqueness_constraint(
    tx: Transaction,
    content_type: ContentTypes,
    prop: str
) -> Result:
    query = NODE_PROPERTY_UNIQUENESS_TEMPLATE.format(label=content_type, prop=prop)
    return tx.run(query)


def create_node_property_existence_constraint(
    tx: Transaction,
    content_type: ContentTypes,
    prop: str,
) -> List[str]:
    query = NODE_PROPERTY_EXISTENCE_TEMPLATE.format(label=content_type, prop=prop)
    return tx.run(query)


def create_relationships_constraints(tx: Transaction) -> List[Result]:
    results: List[Result] = []
    results.append(create_relationship_property_existence_constraint(tx, Rel.DEPENDS_ON, 'mandatorily'))
    return results


def create_relationship_property_existence_constraint(
    tx: Transaction,
    rel: Rel,
    prop: str,
) -> Result:
    query = REL_PROPERTY_EXISTENCE_TEMPLATE.format(label=rel, prop=prop)
    return tx.run(query)
