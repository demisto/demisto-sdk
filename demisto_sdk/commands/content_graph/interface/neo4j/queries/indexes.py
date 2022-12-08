from typing import List

from neo4j import Transaction

from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import run_query

CREATE_NODE_INDEX_TEMPLATE = "CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON ({props})"
NODE_INDEX_OPTIONS = [
    ["id"],
    ["node_id"],
    ["content_type"],
    ["marketplaces"],
    ["object_id"],
    ["object_id", "content_type"],
    ["object_id", "content_type", "fromversion", "marketplaces"],
]

CREATE_REL_INDEX_TEMPLATE = (
    "CREATE INDEX IF NOT EXISTS FOR ()-[r:{rel}]->() ON ({props})"
)


def create_indexes(tx: Transaction) -> None:
    for content_type in ContentType:
        if content_type != ContentType.COMMAND:
            for index_option in NODE_INDEX_OPTIONS:
                create_single_node_index(tx, content_type, index_option)
    create_single_relationship_index(tx, RelationshipType.USES, ["mandatorily"])
    create_single_relationship_index(
        tx, RelationshipType.HAS_COMMAND, ["deprecated", "description"]
    )


def create_single_node_index(
    tx: Transaction,
    content_type: ContentType,
    indexed_properties: List[str],
) -> None:
    properties = ", ".join([f"n.{p}" for p in indexed_properties])
    query = CREATE_NODE_INDEX_TEMPLATE.format(label=content_type, props=properties)
    run_query(tx, query)


def create_single_relationship_index(
    tx: Transaction,
    rel: RelationshipType,
    indexed_properties: List[str],
) -> None:
    properties = ", ".join([f"r.{p}" for p in indexed_properties])
    query = CREATE_REL_INDEX_TEMPLATE.format(rel=rel, props=properties)
    run_query(tx, query)
