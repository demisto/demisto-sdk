from neo4j import Transaction, Result
from typing import List

from demisto_sdk.commands.content_graph.constants import ContentTypes


CREATE_INDEX_TEMPLATE = 'CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON ({props})'
INDEX_OPTIONS = [
    ['node_id'],
    ['id'],
    ['node_id', 'fromversion', 'marketplaces']
]


def create_indexes(tx: Transaction) -> List[Result]:
    results: List[Result] = []
    for content_type in ContentTypes:
        if content_type != ContentTypes.COMMAND:
            for index_option in INDEX_OPTIONS:
                result = create_single_node_index(tx, content_type, index_option)
                results.append(result)
    return results


def create_single_node_index(
    tx: Transaction,
    content_type: ContentTypes,
    indexed_properties: List[str],
) -> Result:
    properties = ', '.join([f'n.{p}' for p in indexed_properties])
    query = CREATE_INDEX_TEMPLATE.format(label=content_type, props=properties)
    result = tx.run(query)
    return result

