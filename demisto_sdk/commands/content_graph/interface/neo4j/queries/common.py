import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.base_content import (
    BaseContent, content_type_to_model)
from neo4j import Result, Transaction

logger = logging.getLogger('demisto-sdk')


class NoModelException(Exception):
    pass


def serialize_node(node: dict, integration_to_commands: Optional[Dict[str, Any]] = None) -> BaseContent:
    content_type = node.get('content_type')
    if not content_type:
        raise NoModelException(f'No content type in the node {node}')
    model = content_type_to_model.get(content_type)
    if not model:
        raise NoModelException(f'No model for {content_type}')
    if integration_to_commands and content_type == ContentType.INTEGRATION and (object_id := node.get('object_id')):
        node['commands'] = integration_to_commands.get(object_id)
    return model.parse_obj(node)


def labels_of(content_type: ContentType) -> str:
    return ':'.join(content_type.labels)


def versioned(property: str) -> str:
    return f'toIntegerList(split({property}, "."))'


def intersects(arr1: str, arr2: str) -> str:
    return f'any(elem IN {arr1} WHERE elem IN {arr2})'


def node_map(properties: Dict[str, Any]) -> str:
    """ Returns a string representation of a map in neo4j format. """
    return f'{{{", ".join([f"{k}: {v}" for k, v in properties.items()])}}}'


def to_neo4j_map(properties: dict) -> str:
    properties = {k: f'"{v}"' if isinstance(v, str) else v for k, v in properties.items()}
    params_str = ', '.join(f'{k}: {v}' for k, v in properties.items())
    params_str = f'{{{params_str}}}' if params_str else ''
    return params_str


def run_query(tx: Transaction, query: str, **kwargs: Dict[str, Any]) -> Result:
    try:
        start_time: datetime = datetime.now()
        logger.info(f'Running query:\n{query}')
        result = tx.run(query, **kwargs)
        logger.info(f'Took {(datetime.now() - start_time).total_seconds()} seconds')
        return result
    except Exception as e:
        logger.error(traceback.format_exc())
        raise e
