import logging
from neo4j import Transaction
from typing import Any, Dict, List
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import run_query, versioned, intersects


logger = logging.getLogger('demisto-sdk')


CREATE_NODES_BY_TYPE_TEMPLATE = """
UNWIND $data AS node_data
CREATE (n:{labels}{{id: node_data.id}})
SET n += node_data
RETURN count(n) AS nodes_created
"""

FIND_DUPLICATES = f"""
MATCH (a:{ContentTypes.BASE_CONTENT})
MATCH (b:{ContentTypes.BASE_CONTENT}{'{node_id: a.node_id}'})
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
    nodes: Dict[ContentTypes, List[Dict[str, Any]]],
) -> None:
    for content_type, data in nodes.items():
        create_nodes_by_type(tx, content_type, data)


def duplicates_exist(tx) -> bool:
    result = run_query(tx, FIND_DUPLICATES).single()
    return result['found_duplicates']


def create_nodes_by_type(
    tx: Transaction,
    content_type: ContentTypes,
    data: List[Dict[str, Any]],
) -> None:
    labels: str = ':'.join(content_type.labels)
    query = CREATE_NODES_BY_TYPE_TEMPLATE.format(labels=labels)
    result = run_query(tx, query, data=data).single()
    nodes_count: int = result['nodes_created']
    logger.info(f'Created {nodes_count} nodes of type {content_type}.')


def get_packs_content_items(
    tx: Transaction,
    marketplace: MarketplaceVersions,
):
    query = f"""
    MATCH (n:{ContentTypes.PACK})<-[:{Rel.IN_PACK}]-(c:{ContentTypes.BASE_CONTENT})
    WHERE n.marketplaces CONTAINS {marketplace}
    RETURN p as pack, collect(c) AS content_items
    """
    return run_query(tx, query).data()
