import os

from neo4j.exceptions import (
    ClientError,
    DatabaseError,
    ServiceUnavailable,
    TransactionError,
)

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.logger import logger


def recover_if_fails(func):
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ServiceUnavailable, DatabaseError, TransactionError, ClientError) as e:
            if os.getenv("CI"):
                logger.error(
                    "Failed to communicate with Neo4j in CI environment", exc_info=True
                )
                raise
            if not neo4j_service.is_running_on_docker():
                logger.error(
                    "Either start the Docker service or install Neo4j locally with this guide: https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/content_graph/README.md",
                    exc_info=True,
                )
                raise
            logger.warning(
                f"Failed to build content graph, retrying with a clean environment. Error: {e}",
            )
            neo4j_service.stop(force=True, clean=True)
            neo4j_service.start()
            return func(*args, **kwargs)

    return func_wrapper
