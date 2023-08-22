import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from neo4j import Result, Transaction
from packaging.version import Version

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType

MAX_RETRIES_QUERY = 3
QUERY_TIMEOUT = 10


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
        k: f'"{v}"' if isinstance(v, (str, Path)) else v for k, v in properties.items()
    }
    params_str = ", ".join(f"{k}: {v}" for k, v in properties.items())
    params_str = f"{{{params_str}}}" if params_str else ""
    return params_str


def run_query(tx: Transaction, query: str, **kwargs) -> Result:
    result = None
    try:
        start_time: datetime = datetime.now()
        logger.debug(f"Running query:\n{query}")
        # invoke a new thread and execute `tx.run in a thread. If the query times out, retry.
        for retry in range(MAX_RETRIES_QUERY):
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(tx.run, query, **kwargs)
                    result = future.result(timeout=QUERY_TIMEOUT)
                    break
            except TimeoutError:
                logger.debug(
                    f"Query timed out, retrying. Retry {retry + 1} out of {MAX_RETRIES_QUERY}"
                )
                continue
        if not result:
            raise TimeoutError(
                f"Query:\n {query} \n timed out after {MAX_RETRIES_QUERY} retries"
            )
        logger.debug(f"Took {(datetime.now() - start_time).total_seconds()} seconds")
        return result
    except Exception as e:
        logger.error(traceback.format_exc())
        raise e
