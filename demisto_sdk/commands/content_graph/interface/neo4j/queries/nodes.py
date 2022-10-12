import logging
from typing import Any, Dict, List, Optional

from neo4j import Transaction

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import (SERVER_CONTENT_ITEMS,
                                                       ContentType,
                                                       Relationship)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
    intersects, run_query, versioned)

logger = logging.getLogger('demisto-sdk')


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
    should_have_lowercase_id: bool = content_type in [ContentType.INCIDENT_FIELD, ContentType.INDICATOR_FIELD]
    data = [{
        'name': content_item,
        'object_id': content_item.lower() if should_have_lowercase_id else content_item,
        'content_type': content_type,
        'is_server_item': True,
    } for content_item in content_items]
    create_nodes_by_type(tx, content_type, data)


def duplicates_exist(tx) -> bool:
    result = run_query(tx, FIND_DUPLICATES).single()
    return result['found_duplicates']


def create_nodes_by_type(
    tx: Transaction,
    content_type: ContentType,
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
    MATCH (p:{ContentType.PACK})<-[:{Relationship.IN_PACK}]-(c:{ContentType.BASE_CONTENT})
    WHERE '{marketplace}' IN p.marketplaces
    RETURN p AS pack, collect(c) AS content_items
    """
    return run_query(tx, query).data()


def get_all_integrations_with_commands(
    tx: Transaction
):
    query = f"""
    MATCH (i:{ContentType.INTEGRATION})-[r:{Relationship.HAS_COMMAND}]->(c:{ContentType.COMMAND})
    WITH i, {{name: c.name, description: r.description, deprecated: r.deprecated}} AS command_data
    RETURN i.object_id AS integration_id, collect(command_data) AS commands
    """
    return run_query(tx, query).data()


def get_nodes_by_type(tx: Transaction, content_type: ContentType):
    query = f"""
    MATCH (node:{content_type}) return node
    """
    return run_query(tx, query).data()


def search_nodes(
    tx: Transaction,
    content_type: Optional[ContentType] = None,
    single_result: bool = False,
    **properties
):
    if not content_type and properties:
        content_type = ContentType.BASE_CONTENT
    content_type_str = f':{content_type}' if content_type else ''
    params_str = ', '.join(f'{k}: "{v}"' for k, v in properties.items())
    params_str = f'{{{params_str}}}' if params_str else ''
    query = f"""
    MATCH (node{content_type_str}{params_str}) return node
    """
    if single_result:
        return run_query(tx, query).single()['node']
    return run_query(tx, query).data()


def delete_all_graph_nodes(
    tx: Transaction
) -> None:
    query = """
    MATCH (n)
    DETACH DELETE n
    """
    run_query(tx, query)
