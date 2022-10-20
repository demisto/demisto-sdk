import itertools
import logging
from typing import Any, Dict, List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import (SERVER_CONTENT_ITEMS,
                                                       ContentType,
                                                       Relationship)
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import (
    intersects, run_query, serialize_node, to_neo4j_map, versioned)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.integration import Integration

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


def _generic_query(
    marketplace: MarketplaceVersions,
    content_type: ContentType,
    filter_by: Optional[str] = None,
    **properties,
) -> str:
    params_str = to_neo4j_map(properties)
    query = f"""
    MATCH (n:{content_type}{params_str})
    WHERE {f"{filter_by} AND" if filter_by else ""} '{marketplace}' IN n.marketplaces
    RETURN n{{.*, id:id(n)}}
    """
    return query


def _base_content_query(
    marketplace: MarketplaceVersions,
    filter_by: Optional[str] = None,
    **properties
) -> str:
    params_str = to_neo4j_map(properties)

    query = f"""
    MATCH (n:{ContentType.BASE_CONTENT}:{params_str})
    WHERE {f"{filter_by} AND" if filter_by else ""} '{marketplace}' IN n.marketplaces
    # if this is an integration
    OPTIONAL MATCH (cmd1)<-[r_cmd1:{Relationship.HAS_COMMAND}]-(n)
    
    # if this is a pack
    OPTIONAL MATCH (content_item)-[:{Relationship.IN_PACK}]->(n)
    WHERE '{marketplace} IN content.item.marketplaces
    OPTIONAL MATCH (cmd2)<-[r_cmd2:{Relationship.HAS_COMMAND}]-(content_item)
    
    # collect commands for pack
    WITH collect({{name: cmd2.name, description: r_cmd2.description, deprecated: r_cmd2.deprecated}}) as commands_inner, cmd1, r_cmd1, n, content_item
    
    # collect commands for integration
    WITH collect({{name: cmd1.name, description: r_cmd1.description, deprecated: r_cmd1.deprecated}}) as commands, n, content_item, commands_inner
    
    # collect content items for pack
    WITH content_item{{.*, commands:commands_inner, id: id(content_item)}} as content_item, n, commands
    WITH collect(content_item) as content_items, n, commands
    
    # return any content item
    RETURN n{{.*, content_items: content_items, commands: commands, id: id(n)}}
    """
    return query


def _packs_query(
    marketplace: MarketplaceVersions,
    filter_by: Optional[str] = None,
    **properties
) -> str:
    params_str = to_neo4j_map(properties)

    query = f"""
    MATCH (n:{ContentType.PACK}{params_str}) -[:{Relationship.IN_PACK}]-(content_item:{ContentType.BASE_CONTENT})
    OPTIONAL MATCH (content_item)-[r:{Relationship.HAS_COMMAND}]->(cmd)
    WITH content_item, [val in collect({{name: cmd.name, description: r.description, deprecated: r.deprecated}}) WHERE val.name is not null] as commands, n
    WITH content_item{{.*, commands: commands, element_id: id(content_item)}}, n
    WITH collect(content_item) as content_items_list, n
    RETURN n{{.*, content_items_list: content_items_list, element_id: id(n)}}    
    """
    return query


def _integrations_query(
    marketplace: MarketplaceVersions,
    filter_by: Optional[str] = None,
    **properties,
) -> str:

    params_str = to_neo4j_map(properties)
    query = f"""
    MATCH (n:{ContentType.INTEGRATION}{params_str})-[{Relationship.HAS_COMMAND}]->(cmd)
    WHERE {f"{filter_by} AND" if filter_by else ""} '{marketplace}' IN n.marketplaces

    WITH collect({{name: cmd.name, description: r.description, deprecated: r.deprecated}}) as commands, n
    RETURN n{{.*, commands: commands, element_id: id(n)}}
    """
    return query


def search_nodes(
    tx: Transaction,
    marketplace: MarketplaceVersions,
    content_type: Optional[ContentType],
    filter_by: Optional[str] = None,
    **properties
) -> List[BaseContent]:
    if not content_type or content_type in ContentType.BASE_CONTENT:
        query = _base_content_query(marketplace, filter_by, **properties)
    elif content_type == ContentType.PACK:
        query = _packs_query(marketplace, filter_by, **properties)
    elif content_type == ContentType.INTEGRATION:
        query = _integrations_query(marketplace, filter_by, **properties)
    else:
        query = _generic_query(marketplace, content_type, filter_by, **properties)
    data = run_query(tx, query).data()
    return [serialize_node(node.get('n')) for node in data]


def delete_all_graph_nodes(
    tx: Transaction
) -> None:
    query = """
    MATCH (n)
    DETACH DELETE n
    """
    run_query(tx, query)
