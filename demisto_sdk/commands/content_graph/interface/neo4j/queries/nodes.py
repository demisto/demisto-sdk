from typing import Any, Dict, Iterable, List, Optional

from neo4j import Transaction, graph

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import (
    CONTENT_PRIVATE_ITEMS,
    ContentType,
    RelationshipType,
    get_server_content_items,
)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
    run_query,
    to_node_pattern,
)

NESTING_LEVEL = 5

LIST_PROPERTIES: List[str] = []

CREATE_CONTENT_ITEM_NODES_BY_TYPE_TEMPLATE = """// Creates content items with labels {labels}
UNWIND $data AS node_data
CREATE (n:{labels}{{
    object_id: node_data.object_id,
    fromversion: node_data.fromversion,
    marketplaces: node_data.marketplaces
}})
SET n = node_data,
    n.not_in_repository = false
WITH n
    OPTIONAL MATCH (n)-[r]->()
    DELETE r
RETURN count(n) AS nodes_created"""


CREATE_NODES_BY_TYPE_TEMPLATE = """// Creates/overrides existing nodes with labels {labels}
UNWIND $data AS node_data
MERGE (n:{labels}{{object_id: node_data.object_id}})
SET n = node_data,  // override existing data
    n.not_in_repository = false
RETURN count(n) AS nodes_created"""


REMOVE_NODES_BY_TYPE = """// Removes parsed nodes of type {content_type} (according to constants)
MATCH (a)
WHERE (a:{label} OR a.content_type = "{content_type}")
AND a.not_in_repository = true
AND any(
    identifier IN [a.object_id, a.name]
    WHERE toLower(identifier) IN {content_items_identifiers}
)
DETACH DELETE a"""


REMOVE_EMPTY_PROPERTIES = """// Removes string properties with empty values ("") from nodes
CALL apoc.periodic.iterate(
    "MATCH (n) RETURN n",
    "WITH n, [key in keys(n) WHERE n[key] = '' | [key, null]] as nullifiers
    WHERE size(nullifiers) <> 0
    WITH n, apoc.map.fromPairs(nullifiers) as nullifyMap
    SET n += nullifyMap",
    {batchSize:30000, parallel:true, iterateList:true}
);"""


def get_relationships_to_preserve(
    tx: Transaction,
    pack_ids: List[str],
) -> List[Dict[str, Any]]:
    """
    Get the relationships to preserve before removing packs
    """
    query = f"""// Gets the relationships to preserve before removing packs
MATCH (s)-[r]->(t)-[:{RelationshipType.IN_PACK}]->(p)
WHERE NOT (s)-[:{RelationshipType.IN_PACK}]->(p)
AND p.object_id in {pack_ids}
RETURN elementId(s) as source_id, s as source, type(r) as r_type, properties(r) as r_properties, t as target

UNION

MATCH (s)-[r]->(t)<-[:{RelationshipType.HAS_COMMAND}]-()-[:{RelationshipType.IN_PACK}]->(p)
WHERE NOT (s)-[:{RelationshipType.IN_PACK}]->(p)
AND p.object_id in {pack_ids}
RETURN elementId(s) as source_id, s as source, type(r) as r_type, properties(r) as r_properties, t as target

UNION

MATCH (s)-[r]->(t)
WHERE NOT (s)-[:{RelationshipType.IN_PACK}]->(t)
AND t.object_id in {pack_ids}
RETURN elementId(s) as source_id, s as source, type(r) as r_type, properties(r) as r_properties, t as target"""
    return run_query(tx, query).data()


def remove_packs_before_creation(
    tx: Transaction,
    pack_ids: List[str],
) -> None:
    query = f"""// Removes packs commands before recreating them
MATCH (c)<-[:{RelationshipType.HAS_COMMAND}]-()-[:{RelationshipType.IN_PACK}]->(p)
WHERE p.object_id IN {pack_ids}
OPTIONAL MATCH (c)<-[:{RelationshipType.HAS_COMMAND}]-()-[:{RelationshipType.IN_PACK}]->(p2)
WHERE NOT p2.object_id IN {pack_ids}
WITH c, p2
WHERE p2 IS NULL
DETACH DELETE c
"""
    run_query(tx, query)
    query = f"""// Removes packs and their content items before recreating them
MATCH (n)-[:{RelationshipType.IN_PACK}]->(p)
WHERE p.object_id in {pack_ids}
DETACH DELETE n, p"""
    run_query(tx, query)


def return_preserved_relationships(
    tx: Transaction, rels_to_preserve: List[Dict[str, Any]]
) -> None:
    """We search for source nodes which are in the preserved relationships, and they are the same nodes (same object_id and content_type)"""
    query = f"""// Returns the preserved relationships
UNWIND $rels_data AS rel_data
MATCH (s) WHERE elementId(s) = rel_data.source_id AND s.object_id = rel_data.source.object_id AND s.content_type = rel_data.source.content_type
OPTIONAL MATCH (t:{ContentType.BASE_NODE}{{
    object_id: rel_data.target.object_id,
    content_type: rel_data.target.content_type
}})
WITH s, t, rel_data
WHERE NOT t IS NULL
CALL apoc.create.relationship(s, rel_data.r_type, rel_data.r_properties, t)
YIELD rel
RETURN rel"""
    run_query(tx, query, rels_data=rels_to_preserve)


def create_nodes(
    tx: Transaction,
    nodes: Dict[ContentType, List[Dict[str, Any]]],
) -> None:
    for content_type, data in nodes.items():
        create_nodes_by_type(tx, content_type, data)


def remove_nodes(tx: Transaction, content_type_to_identifiers: dict) -> None:
    for content_type, content_items_identifiers in content_type_to_identifiers.items():
        if content_type in [ContentType.COMMAND, ContentType.SCRIPT]:
            label = ContentType.COMMAND_OR_SCRIPT
        else:
            label = ContentType.BASE_NODE

        query = REMOVE_NODES_BY_TYPE.format(
            label=label,
            content_type=content_type,
            content_items_identifiers=[c.lower() for c in content_items_identifiers],
        )
        run_query(tx, query)


def remove_server_nodes(tx: Transaction) -> None:
    remove_nodes(tx, get_server_content_items())


def remove_content_private_nodes(tx: Transaction) -> None:
    remove_nodes(tx, CONTENT_PRIVATE_ITEMS)


def create_nodes_by_type(
    tx: Transaction,
    content_type: ContentType,
    data: List[Dict[str, Any]],
) -> None:
    labels: str = ":".join(content_type.labels)
    if content_type in ContentType.content_items():
        query = CREATE_CONTENT_ITEM_NODES_BY_TYPE_TEMPLATE.format(labels=labels)
    else:
        query = CREATE_NODES_BY_TYPE_TEMPLATE.format(labels=labels)
    result = run_query(tx, query, data=data).single()
    nodes_count: int = result["nodes_created"]
    logger.debug(f"Created {nodes_count} nodes of type {content_type}.")


def _match(
    tx: Transaction,
    marketplace: MarketplaceVersions = None,
    content_type: ContentType = ContentType.BASE_NODE,
    ids_list: Optional[Iterable[int]] = None,
    **properties,
) -> List[graph.Node]:
    """A query to match nodes in the graph.

    Args:
        tx: Neo4j transaction.
        marketplace: The marketplace to filter by.
        content_type: The content type to filter by.
        ids_list: A list of neo4j ids to filter by.

    Returns:
        List[graph.Node]: list of neo4j nodes.
    """
    if marketplace:
        properties["marketplaces"] = marketplace.value

    query = f"""// Retrieves nodes according to given parameters.
MATCH {to_node_pattern(properties, content_type=content_type, list_properties=get_list_properties(tx))}
{"WHERE elementId(node) IN $filter_list" if ids_list else ""}
RETURN node"""

    return [
        item.get("node")
        for item in run_query(
            tx, query, filter_list=list(ids_list) if ids_list else None
        )
    ]


def get_schema(tx: Transaction) -> dict:
    """Get the schema of the graph.

    Args:
        tx: Neo4j transaction.

    Returns:
        dict: The schema of the graph.
    """
    query = """// Retrieves the schema of the graph.
    CALL apoc.meta.schema()
    YIELD value
    UNWIND keys(value) AS label
    RETURN label, keys(value[label].properties) as properties
    """
    return {item["label"]: item["properties"] for item in run_query(tx, query).data()}


def get_list_properties(tx: Transaction) -> List[str]:
    """
    Get all list properties in the graph
    We will store the result in the global variable of LIST_PROPERTIES, so we will not need to run this query again

    Note: The reason we don't use cache decorator is because we want to cache this data for different transactions.
    """
    global LIST_PROPERTIES
    if LIST_PROPERTIES:
        return LIST_PROPERTIES
    query = """
    CALL apoc.meta.schema()
    YIELD value
    UNWIND keys(value) AS label
    UNWIND keys(value[label].properties) AS property
    WITH label, property, value[label].properties[property] AS schema
    WHERE schema.type = "LIST"
    RETURN collect(distinct property) as list_properties
    """
    LIST_PROPERTIES = run_query(tx, query).single()["list_properties"]
    return LIST_PROPERTIES


def delete_all_graph_nodes(tx: Transaction) -> None:
    query = """// Deletes all graph nodes and relationships
MATCH (n)
DETACH DELETE n"""
    run_query(tx, query)


def remove_empty_properties(tx: Transaction) -> None:
    run_query(tx, REMOVE_EMPTY_PROPERTIES)
