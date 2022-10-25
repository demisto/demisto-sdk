import logging
from itertools import chain
from typing import Any, Dict, Iterable, List, Optional, Tuple

from neo4j import Transaction, graph

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import (SERVER_CONTENT_ITEMS,
                                                       ContentType)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
    intersects, run_query, to_neo4j_map, versioned)

logger = logging.getLogger("demisto-sdk")

NESTING_LEVEL = 5

CREATE_NODES_BY_TYPE_TEMPLATE = """
UNWIND $data AS node_data
CREATE (n:{labels}{{object_id: node_data.object_id}})
SET n += node_data
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


def create_nodes(
    tx: Transaction,
    nodes: Dict[ContentType, List[Dict[str, Any]]],
) -> None:
    for content_type, data in nodes.items():
        create_nodes_by_type(tx, content_type, data)
    for content_type, content_items in SERVER_CONTENT_ITEMS.items():
        create_server_nodes_by_type(tx, content_type, content_items)


def create_server_nodes_by_type(
    tx: Transaction,
    content_type: ContentType,
    content_items: List[str],
) -> None:
    should_have_lowercase_id: bool = content_type in [
        ContentType.INCIDENT_FIELD,
        ContentType.INDICATOR_FIELD,
    ]
    data = [
        {
            "name": content_item,
            "object_id": content_item.lower()
            if should_have_lowercase_id
            else content_item,
            "content_type": content_type,
            "is_server_item": True,
        }
        for content_item in content_items
    ]
    create_nodes_by_type(tx, content_type, data)


def duplicates_exist(tx) -> bool:
    result = run_query(tx, FIND_DUPLICATES).single()
    return result["found_duplicates"]


def create_nodes_by_type(
    tx: Transaction,
    content_type: ContentType,
    data: List[Dict[str, Any]],
) -> None:
    labels: str = ":".join(content_type.labels)
    query = CREATE_NODES_BY_TYPE_TEMPLATE.format(labels=labels)
    result = run_query(tx, query, data=data).single()
    nodes_count: int = result["nodes_created"]
    logger.info(f"Created {nodes_count} nodes of type {content_type}.")


def _match(
    tx: Transaction,
    marketplace: MarketplaceVersions,
    content_type: Optional[ContentType],
    filter_list: Optional[Iterable[int]] = None,
    is_nested: bool = False,
    **properties,
) -> List[Tuple[graph.Node, List[graph.Relationship], List[graph.Node]]]:
    params_str = to_neo4j_map(properties)

    content_type_str = f":{content_type}" if content_type else ""
    nesting_str = f"*..{NESTING_LEVEL}" if is_nested else ""

    query = f"""
    MATCH (n{content_type_str}{params_str}) - [r{nesting_str}] - (k)
    WHERE {"id(n) IN $filter_list AND" if filter_list else ""} '{marketplace}' IN n.marketplaces AND '{marketplace}' IN k.marketplaces
    RETURN n, collect(r) as rels, collect(k) as ks
    """
    result = []
    for item in run_query(
        tx, query, filter_list=list(filter_list) if filter_list else None
    ):
        rels = item.get("rels")
        if any(isinstance(el, list) for el in rels):
            rels = list(chain.from_iterable(rels))

        ks = item.get("ks")
        if any(isinstance(el, list) for el in ks):
            ks = list(chain.from_iterable(ks))

        result.append((item.get("n"), rels, ks))
    return result


def delete_all_graph_nodes(tx: Transaction) -> None:
    query = """
    MATCH (n)
    DETACH DELETE n
    """
    run_query(tx, query)
