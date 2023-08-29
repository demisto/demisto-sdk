import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

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


def to_neo4j_map(
    properties: dict, node_variable_name: str = "node"
) -> Tuple[str, list]:
    """This function is used to filter nodes by their properties.

    Args:
        properties (dict): The properties to filter by.
        node_variable_name (str, optional): The variable name of the node in the neo4j query. Defaults to "node".

    Returns:
        Tuple[str, list]: The first value is a map of neo4j properties to filter in a query.
                          The second value is a list of where clauses to filter in a query.

    """
    updated_properties = {}
    where_clause = []
    for key, prop in properties.items():
        if isinstance(prop, (str, Path)):
            updated_properties[key] = f"'{prop}'"
        elif isinstance(prop, bool):
            updated_properties[key] = str(prop).lower()
        elif isinstance(prop, Iterable):
            where_clause.append(f"{node_variable_name}.{key} IN {list(prop)}")
    params_str = ", ".join(f"{k}: {v}" for k, v in updated_properties.items())
    params_str = f"{{{params_str}}}" if params_str else ""
    return params_str, where_clause


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
