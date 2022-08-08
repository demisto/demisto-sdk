from datetime import datetime
from neo4j import Transaction, Result
from typing import Any, Dict

import logging


logger = logging.getLogger('demisto-sdk')


def run_query(tx: Transaction, query: str, **kwargs: Dict[str, Any]) -> Result:
    try:
        start_time: datetime = datetime.now()
        logger.info(f'Running query:\n{query}')
        result = tx.run(query, **kwargs)
        logger.info(f'Took {(datetime.now() - start_time).total_seconds()} seconds')
        return result
    except Exception as e:
        logger.error(str(e))
        raise e
