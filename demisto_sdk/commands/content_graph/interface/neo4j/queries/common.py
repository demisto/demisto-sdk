from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

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
    """This function creates a neo4j map cypher query.
    The idea is to filter the node by the given properties.

    Args:
        properties (dict): The properties to filter by.

    Returns:
        str: The neo4j map cypher query.
    """
    properties = {
        k: f'"{v}"' if isinstance(v, (str, Path)) else str(v).lower()
        for k, v in properties.items()
    }
    params_str = ", ".join(f"{k}: {v}" for k, v in properties.items())
    return f"{{{params_str}}}" if params_str else ""


def to_neo4j_predicates(
    properties: dict, varname: str = "node", list_properties: Optional[List[str]] = None
) -> str:
    """This function creates a neo4j predicates cypher query.
    The idea is to create a predicates which will filter the node by the properties, in case we cannot use neo4j map.

    Args:
        properties (dict): The properties to filter by.
        varname (str, optional): The varname of the node of the query. Defaults to "node".
        list_properties (Optional[List[str]], optional): List of list properties in the neo4j database. Defaults to None.

    Returns:
        str: The neo4j predicates cypher query.
    """
    if not list_properties:
        list_properties = []
    predicates = [
        f"{varname}.{k} IN {list(v)}"
        for k, v in properties.items()
        if k not in list_properties
    ]

    list_predicates = [
        f"'{v}' IN {varname}.{k}" for k, v in properties.items() if k in list_properties
    ]
    return (
        f"WHERE {' AND '.join(predicates + list_predicates)}"
        if predicates or list_predicates
        else ""
    )


def to_node_pattern(
    properties: dict,
    varname: str = "node",
    content_type: ContentType = ContentType.BASE_NODE,
    list_properties: Optional[List[str]] = None,
) -> str:
    """
    This function creates a node pattern cypher query.
    The idea is to create a node pattern which will filter the node by the content type and the propertes

    Args:
        properties (dict): The properties to filter by.
        varname (str, optional): The varname of the node of the query. Defaults to "node".
        content_type (ContentType, optional): The content type to filter on. Defaults to ContentType.BASE_NODE.
        list_properties (Optional[List[str]], optional): List of list properties in the neo4j database. Defaults to None.

    Returns:
        str: The node pattern cypher query.
    """
    if not list_properties:
        list_properties = []
    neo4j_primitive_types = (str, bool, Path, int, float)
    exact_match_properties = {
        k: v
        for k, v in properties.items()
        if k not in list_properties and isinstance(v, neo4j_primitive_types)
    }
    predicates_match_properties = {
        k: v
        for k, v in properties.items()
        if k in list_properties
        or (not isinstance(v, neo4j_primitive_types) and isinstance(v, Iterable))
    }
    return f"({varname}:{content_type}{to_neo4j_map(exact_match_properties)} {to_neo4j_predicates(predicates_match_properties, varname, list_properties)})"


def run_query(tx: Transaction, query: str, **kwargs) -> Result:
    start_time: datetime = datetime.now()
    loggable_query = query.replace("<", "\\<")
    logger.debug(f"Running query:\n{loggable_query}")

    try:
        result = tx.run(query, **kwargs)
    except Exception:
        logger.exception("Query failed")
        raise

    logger.debug(f"Took {(datetime.now() - start_time).total_seconds()} seconds")
    return result
