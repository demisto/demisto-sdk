from neo4j import Transaction, Result
from typing import List

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.interface.neo4j.queries.common import run_query


CREATE_INDEX_TEMPLATE = 'CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON ({props})'
INDEX_OPTIONS = [
    ['node_id'],
    ['id'],
    ['node_id', 'fromversion', 'marketplaces']
]


def create_indexes(tx: Transaction) -> None:
    for content_type in ContentTypes:
        if content_type != ContentTypes.COMMAND:
            for index_option in INDEX_OPTIONS:
                create_single_node_index(tx, content_type, index_option)


def create_single_node_index(
    tx: Transaction,
    content_type: ContentTypes,
    indexed_properties: List[str],
) -> None:
    properties = ', '.join([f'n.{p}' for p in indexed_properties])
    query = CREATE_INDEX_TEMPLATE.format(label=content_type, props=properties)
    run_query(tx, query)
