import logging
from typing import List

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.content_graph.content_graph_builder import ContentGraphBuilder
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface

logger = logging.getLogger("demisto-sdk")


def create_content_graph(
    content_graph_interface: ContentGraphInterface,
    dependencies: bool = False,
    export: bool = False,
) -> None:
    """This function creates a new content graph database in neo4j from the content path

    Args:
        content_graph_interface (ContentGraphInterface): The content graph interface.
    """
    ContentGraphBuilder(content_graph_interface).create_graph()
    if dependencies:
        content_graph_interface.create_pack_dependencies()
    if export:
        content_graph_interface.export_graph()


def update_content_graph(
    content_graph_interface: ContentGraphInterface,
    packs_to_update: List[str],
    dependencies: bool = False,
) -> None:
    """This function creates a new content graph database in neo4j from the content path
    Args:
        content_graph_interface (ContentGraphInterface): The content graph interface.
    """
    ContentGraphBuilder(content_graph_interface).update_graph(packs_to_update)
    if dependencies:
        content_graph_interface.create_pack_dependencies()
    content_graph_interface.export_graph()


def stop_content_graph(
    use_docker: bool = False,
) -> None:
    """
    This function stops the neo4j service if it is running.

    Args:
        use_docker (bool, optional): Whether or not the service runs with docker.
    """
    neo4j_service.stop(use_docker=use_docker)
