import logging
import traceback
from datetime import datetime
from typing import Any, Dict

from neo4j import Result, Transaction

from demisto_sdk.commands.content_graph.common import ContentType

logger = logging.getLogger("demisto-sdk")


def labels_of(content_type: ContentType) -> str:
    return ":".join(content_type.labels)


def versioned(property: str) -> str:
    return f'toIntegerList(split({property}, "."))'


def intersects(arr1: str, arr2: str) -> str:
    return f"any(elem IN {arr1} WHERE elem IN {arr2})"


def node_map(properties: Dict[str, Any]) -> str:
    """Returns a string representation of a map in neo4j format."""
    return f'{{{", ".join([f"{k}: {v}" for k, v in properties.items()])}}}'


def to_neo4j_map(properties: dict) -> str:
    properties = {
        k: f'"{v}"' if isinstance(v, str) else v for k, v in properties.items()
    }
    params_str = ", ".join(f"{k}: {v}" for k, v in properties.items())
    params_str = f"{{{params_str}}}" if params_str else ""
    return params_str


def run_query(tx: Transaction, query: str, **kwargs: Dict[str, Any]) -> Result:
    try:
        start_time: datetime = datetime.now()
        logger.info(f"Running query:\n{query}")
        result = tx.run(query, **kwargs)
        logger.info(f"Took {(datetime.now() - start_time).total_seconds()} seconds")
        return result
    except Exception as e:
        logger.error(traceback.format_exc())
        raise e
