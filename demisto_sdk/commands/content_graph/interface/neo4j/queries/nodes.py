import logging
from typing import Any, Dict, Iterable, List, Optional

from neo4j import Transaction

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import SERVER_CONTENT_ITEMS, ContentType, Neo4jResult
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (intersects, run_query, to_neo4j_map,
                                                                               versioned)

logger = logging.getLogger("demisto-sdk")

NESTING_LEVEL = 5

CREATE_CONTENT_ITEM_NODES_BY_TYPE_TEMPLATE = """
UNWIND $data AS node_data
MERGE (n:{labels}{{
    object_id: node_data.object_id,
    fromversion: node_data.fromversion,
    marketplaces: node_data.marketplaces
}})
SET n = node_data,  // override existing data
    n.not_in_repository = false
WITH n
    OPTIONAL MATCH (n)-[r]->()
    DELETE r
RETURN count(n) AS nodes_created
"""


CREATE_NODES_BY_TYPE_TEMPLATE = """
UNWIND $data AS node_data
MERGE (n:{labels}{{object_id: node_data.object_id}})
SET n = node_data,  // override existing data
    n.not_in_repository = false
RETURN count(n) AS nodes_created
"""


FIND_DUPLICATES = f"""
MATCH (a:{ContentType.BASE_CONTENT})
MATCH (b:{ContentType.BASE_CONTENT}{'{node_id: a.node_id}'})
WHERE
    id(a) <> id(b)
AND
    {intersects('a.marketplaces', 'b.marketplaces')}
AND
    {versioned('a.toversion')} >= {versioned('b.fromversion')}
AND
    {versioned('b.toversion')} >= {versioned('a.fromversion')}
RETURN count(b) > 0 AS found_duplicates
"""


REMOVE_SERVER_NODES_BY_TYPE = """
MATCH (a)
WHERE (a:{label} OR a.content_type = "{content_type}")
AND a.not_in_repository = true
AND any(
    identifier IN [a.object_id, a.name]
    WHERE toLower(identifier) IN {server_content_items}
)
DETACH DELETE a
"""


def create_nodes(
    tx: Transaction,
    nodes: Dict[ContentType, List[Dict[str, Any]]],
) -> None:
    for content_type, data in nodes.items():
        create_nodes_by_type(tx, content_type, data)


def remove_server_nodes(tx: Transaction) -> None:
    for content_type, content_items in SERVER_CONTENT_ITEMS.items():
        if content_type in [ContentType.COMMAND, ContentType.SCRIPT]:
            label = ContentType.COMMAND_OR_SCRIPT
        else:
            label = ContentType.BASE_CONTENT

        query = REMOVE_SERVER_NODES_BY_TYPE.format(
            label=label,
            content_type=content_type,
            server_content_items=[c.lower() for c in content_items],
        )
        run_query(tx, query)


def duplicates_exist(tx) -> bool:
    result = run_query(tx, FIND_DUPLICATES).single()
    return result["found_duplicates"]


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
    logger.info(f"Created {nodes_count} nodes of type {content_type}.")


def _match(
    tx: Transaction,
    marketplace: MarketplaceVersions = None,
    content_type: Optional[ContentType] = None,
    filter_list: Optional[Iterable[int]] = None,
    **properties,
) -> List[Neo4jResult]:
    params_str = to_neo4j_map(properties)

    content_type_str = f":{content_type}" if content_type else ""
    where = []
    if marketplace or filter_list:
        where.append("WHERE")
        if filter_list:
            where.append("id(node_from) IN $filter_list")
        if filter_list and marketplace:
            where.append("AND")
        if marketplace:
            where.append(f"'{marketplace}' IN node_from.marketplaces AND '{marketplace}' IN node_to.marketplaces")

    query = f"""
    MATCH (node_from{content_type_str}{params_str}) - [relationship] - (node_to)
    {" ".join(where)}
    RETURN node_from, collect(relationship) as relationships, collect(node_to) as nodes_to
    """
    return [
        Neo4jResult(node_from=item.get("node_from"), relationships=item.get("relationships"), nodes_to=item.get("nodes_to"))
        for item in run_query(tx, query, filter_list=list(filter_list) if filter_list else None)
    ]


def delete_all_graph_nodes(tx: Transaction) -> None:
    query = """
    MATCH (n)
    DETACH DELETE n
    """
    run_query(tx, query)
