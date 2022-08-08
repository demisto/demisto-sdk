import logging
from neo4j import Transaction
from typing import Any, Dict, List

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import run_query


logger = logging.getLogger('demisto-sdk')


CREATE_NODES_BY_TYPE_TEMPLATE = """
    UNWIND $data AS node_data
    CREATE (n:{labels}{{id: node_data.id}})
    SET n += node_data
    RETURN count(n) AS nodes_created
"""


def create_nodes(
    tx: Transaction,
    nodes: Dict[ContentTypes, List[Dict[str, Any]]],
) -> None:
    for content_type, data in nodes.items():
        create_nodes_by_type(tx, content_type, data)



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