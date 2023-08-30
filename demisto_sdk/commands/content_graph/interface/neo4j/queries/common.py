import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable

from neo4j import Result, Transaction
from packaging.version import Version

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType


def labels_of(content_type: ContentType) -> str:
    return ":".join(content_type.labels)


def versioned(property: str) -> str:
    try:
        Version(property)
        property = f'"{property}"'
    except Exception:
        pass
    return f'toIntegerList(split({property}, "."))'


def intersects(arr1: str, arr2: str) -> str:
    return f"any(elem IN {arr1} WHERE elem IN {arr2})"


def is_target_available(source: str, target: str) -> str:
    """Builds a query that determines if a target content item is available for use by
    a source content item (i.e. they share a marketplace and have overlapping versions).
    """
    return f"""({intersects(f'{source}.marketplaces', f'{target}.marketplaces')}
AND
    {versioned(f'{source}.toversion')} >= {versioned(f'{target}.fromversion')}
AND
    {versioned(f'{target}.toversion')} >= {versioned(f'{source}.fromversion')})
    """


def node_map(properties: Dict[str, Any]) -> str:
    """Returns a string representation of a map in neo4j format."""
    return f'{{{", ".join([f"{k}: {v}" for k, v in properties.items()])}}}'


def to_neo4j_map(properties: dict) -> str:
    properties = {
        k: f'"{v}"' if isinstance(v, (str, Path)) else str(v).lower()
        for k, v in properties.items()
    }
    params_str = ", ".join(f"{k}: {v}" for k, v in properties.items())
    return f"{{{params_str}}}" if params_str else ""


def to_neo4j_predicates(properties: dict, varname: str = "node") -> str:
    predicates = [f"{varname}.{k} IN {list(v)}" for k, v in properties.items()]
    return f"WHERE {' AND '.join(predicates)}" if predicates else ""


def to_node_pattern(
    properties: dict,
    varname: str = "node",
    content_type: ContentType = ContentType.BASE_CONTENT,
) -> str:
    if not content_type:
        content_type = ContentType.BASE_CONTENT
    neo4j_primitive_types = (str, bool, Path)
    exact_match_properties = {
        k: v for k, v in properties.items() if isinstance(v, neo4j_primitive_types)
    }
    predicates_match_properties = {
        k: v
        for k, v in properties.items()
        if not isinstance(v, neo4j_primitive_types) and isinstance(v, Iterable)
    }
    return f"({varname}:{labels_of(content_type)}{to_neo4j_map(exact_match_properties)} {to_neo4j_predicates(predicates_match_properties, varname)})"


def run_query(tx: Transaction, query: str, **kwargs) -> Result:
    try:
        start_time: datetime = datetime.now()
        logger.debug(f"Running query:\n{query}")
        result = tx.run(query, **kwargs)
        logger.debug(f"Took {(datetime.now() - start_time).total_seconds()} seconds")
        return result
    except Exception as e:
        logger.error(traceback.format_exc())
        raise e
