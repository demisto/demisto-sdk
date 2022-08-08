from neo4j import Transaction, Result
from typing import Any, Dict, List

from demisto_sdk.commands.content_graph.constants import ContentTypes


CREATE_NODES_BY_TYPE_TEMPLATE = """
    UNWIND $data AS node_data
    CREATE (n:{labels}{{id: node_data.id}})
    SET n += node_data
"""


def create_nodes(
    tx: Transaction,
    nodes: Dict[ContentTypes, List[Dict[str, Any]]],
) -> List[Result]:
    results: List[Result] = []
    for content_type, data in nodes.items():
        results.append(create_nodes_by_type(tx, content_type, data))


def create_nodes_by_type(
    tx: Transaction,
    content_type: ContentTypes,
    data: List[Dict[str, Any]],
) -> str:
    labels: str = ':'.join(content_type.labels)
    query = CREATE_NODES_BY_TYPE_TEMPLATE.format(labels=labels)
    result = tx.run(query, data=data)
    return result
