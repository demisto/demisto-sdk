import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import (SERVER_CONTENT_ITEMS,
                                                       ContentType,
                                                       Relationship)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
    intersects, run_query, serialize_node, versioned)
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.integration import Command
from demisto_sdk.commands.content_graph.objects.pack import Pack
from neo4j import Transaction

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


def get_packs(
    tx: Transaction,
    marketplace: MarketplaceVersions,
    **properties,
) -> List[Pack]:
    params_str = ', '.join(f'{k}: "{v}"' for k, v in properties.items())
    params_str = f'{{{params_str}}}' if params_str else ''
    query = f"""
    MATCH (p:{ContentType.PACK}{params_str})<-[:{Relationship.IN_PACK}]-(c:{ContentType.BASE_CONTENT})
    WHERE '{marketplace}' IN p.marketplaces AND '{marketplace}' IN c.marketplaces
    RETURN p AS pack, collect(c) AS content_items
    """
    packs: List[Pack] = []
    integrations_to_commands = _get_all_integrations_with_commands(tx)
    for item in run_query(tx, query).data():
        pack = item.get('pack')
        content_items = item.get('content_items')
        content_items_dct: Dict[str, Any] = {}
        for content_item in content_items:
            content_item_id = content_item['object_id']
            if (content_type := content_item['content_type']) == ContentType.INTEGRATION:
                content_item['commands'] = integrations_to_commands.get(content_item_id, [])
            content_items_dct.setdefault(content_type, []).append(content_item)
        pack['content_items'] = content_items_dct
        packs.append(Pack.parse_obj(pack))
    return packs


def _get_all_integrations_with_commands(
    tx: Transaction
):
    query = f"""
    MATCH (i:{ContentType.INTEGRATION})-[r:{Relationship.HAS_COMMAND}]->(c:{ContentType.COMMAND})
    WITH i, {{name: c.name, description: r.description, deprecated: r.deprecated}} AS command_data
    RETURN i.object_id AS integration_id, collect(command_data) AS commands
    """
    return {data.get('integration_id'): data.get('commands', []) for data in run_query(tx, query).data()}


def search_nodes(
    tx: Transaction,
    marketplace: MarketplaceVersions,
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
    MATCH (node{content_type_str}{params_str})
    WHERE '{marketplace}' IN node.marketplaces
    RETURN node
    """
    data = run_query(tx, query).data()
    integration_to_commands = None
    if ContentType.INTEGRATION in {node.get('content_type') for node in data}:
        integration_to_commands = _get_all_integrations_with_commands(tx)
    serialized_data = [serialize_node(node.get('node'), integration_to_commands) for node in data]
    if single_result and serialized_data:
        return serialized_data[0]
    return serialized_data


def delete_all_graph_nodes(
    tx: Transaction
) -> None:
    query = """
    MATCH (n)
    DETACH DELETE n
    """
    run_query(tx, query)
