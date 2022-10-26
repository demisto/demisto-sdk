import logging

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.content_graph.common import REPO_PATH
from demisto_sdk.commands.content_graph.content_graph_builder import \
    ContentGraphBuilder
from demisto_sdk.commands.content_graph.interface.graph import \
    ContentGraphInterface

logger = logging.getLogger("demisto-sdk")


def create_content_graph(
    content_graph_interface: ContentGraphInterface,
) -> None:
    """This function creates a new content graph database in neo4j from the content path

    Args:
        content_graph_interface (ContentGraphInterface): The content graph interface.
    """
    content_graph_builder = ContentGraphBuilder(REPO_PATH, content_graph_interface)
    content_graph_builder.create_graph()


def stop_content_graph(
    use_docker: bool = False,
) -> None:
    """
    This function stops the neo4j service if it is running.

    Args:
        use_docker (bool, optional): Whether or not the service runs with docker.
    """
    neo4j_service.stop(use_docker=use_docker)
