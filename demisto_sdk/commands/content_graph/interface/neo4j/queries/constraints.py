from neo4j import Transaction

from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import run_query

# CONSTRAINT NAMES
CMD_UNIQUE_OBJ_ID = "cmd_unique_object_id"

DROP_CONSTRAINT_TEMPLATE = "DROP CONSTRAINT {name} IF EXISTS"

NODE_PROPERTY_UNIQUENESS_TEMPLATE = (
    "CREATE CONSTRAINT {name} IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
)
NODE_PROPERTY_EXISTENCE_TEMPLATE = (
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS NOT NULL"
)
REL_PROPERTY_EXISTENCE_TEMPLATE = (
    "CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:{label}]-() REQUIRE r.{prop} IS NOT NULL"
)


def drop_constraints(tx: Transaction) -> None:
    drop_nodes_constraints(tx)


def drop_nodes_constraints(tx: Transaction) -> None:
    drop_node_property_uniqueness_constraint(tx, CMD_UNIQUE_OBJ_ID)


def drop_node_property_uniqueness_constraint(
    tx: Transaction,
    name: str,
) -> None:
    query = DROP_CONSTRAINT_TEMPLATE.format(name=name)
    run_query(tx, query)


def create_constraints(tx: Transaction) -> None:
    create_nodes_constraints(tx)


def create_nodes_constraints(tx: Transaction) -> None:
    create_node_property_uniqueness_constraint(
        tx, CMD_UNIQUE_OBJ_ID, ContentType.COMMAND, "object_id"
    )


def create_node_property_uniqueness_constraint(
    tx: Transaction, name: str, content_type: ContentType, prop: str
) -> None:
    query = NODE_PROPERTY_UNIQUENESS_TEMPLATE.format(
        name=name, label=content_type, prop=prop
    )
    run_query(tx, query)


def create_node_property_existence_constraint(
    tx: Transaction,
    content_type: ContentType,
    prop: str,
) -> None:
    query = NODE_PROPERTY_EXISTENCE_TEMPLATE.format(label=content_type, prop=prop)
    run_query(tx, query)


def create_relationships_constraints(tx: Transaction) -> None:
    create_relationship_property_existence_constraint(
        tx, RelationshipType.DEPENDS_ON, "mandatorily"
    )


def create_relationship_property_existence_constraint(
    tx: Transaction,
    rel: RelationshipType,
    prop: str,
) -> None:
    query = REL_PROPERTY_EXISTENCE_TEMPLATE.format(label=rel, prop=prop)
    run_query(tx, query)
