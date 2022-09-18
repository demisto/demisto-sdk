from datetime import datetime
import traceback
from neo4j import Transaction, Result
from typing import Any, Dict


from demisto_sdk.commands.content_graph.common import ContentType

import logging


logger = logging.getLogger('demisto-sdk')


def labels_of(content_type: ContentType) -> str:
    return ':'.join(content_type.labels)


def versioned(property: str) -> str:
    return f'toIntegerList(split({property}, "."))'


def intersects(arr1: str, arr2: str) -> str:
    return f'any(elem IN {arr1} WHERE elem IN {arr2})'


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
