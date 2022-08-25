import logging
import shutil
from pathlib import Path
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.content_graph_builder import \
    ContentGraphBuilder
from demisto_sdk.commands.content_graph.content_graph_loader import ContentGraphLoader
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface
from demisto_sdk.commands.content_graph.interface.neo4j.queries.nodes import delete_all_graph_nodes
from demisto_sdk.commands.content_graph.interface.neo4j_graph import \
    Neo4jContentGraphInterface

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.content_graph.common import (NEO4J_DATABASE_URL,
                                                       NEO4J_PASSWORD,
                                                       NEO4J_USERNAME,
                                                       REPO_PATH)
from demisto_sdk.commands.content_graph.objects.repository import Repository

logger = logging.getLogger('demisto-sdk')

NEO4J_INTERFACE = Neo4jContentGraphInterface(NEO4J_DATABASE_URL, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))


def create_content_graph(
    use_docker: bool = True,
    use_existing: bool = False,
    should_dump: bool = False,
) -> ContentGraphInterface:
    """This function creates a new content graph database in neo4j from the content path

    Args:
        use_docker (bool, optional): Whether run neo4j in docker. Defaults to True.
        use_existing (bool, optional): Whether use existing service. Defaults to False.

    Returns:
        ContentGraphInterface: The content graph interface that was created.
    """
    if not use_existing:
        shutil.rmtree(REPO_PATH / 'neo4j' / 'data', ignore_errors=True)
        neo4j_service.start_neo4j_service(use_docker)
    content_graph_builder = ContentGraphBuilder(REPO_PATH, NEO4J_INTERFACE)
    content_graph_builder
    content_graph_builder.create_graph()
    if should_dump:
        neo4j_service.dump(use_docker=use_docker)
    return content_graph_builder.content_graph


def load_content_graph(
    use_docker: bool = True,
    content_graph_path: Path = None,
) -> ContentGraphInterface:
    """This function loads a database dump file to the content graph database in neo4j

    Args:
        use_docker (bool, optional): Whether run neo4j in docker. Defaults to True.
        content_graph_path (Path, optional): The dump file path to load from. Defaults to None, which means use the default path.
                                             Default path: (<REPO_PATH>/neo4j/backups/content-graph.dump)

    Returns:
        ContentGraphInterface: The content graph interface that was loaded.
    """
    if content_graph_path and content_graph_path.is_file():
        shutil.copy(content_graph_path, REPO_PATH / 'neo4j' / 'backups' / 'content-graph.dump')
    neo4j_service.load(use_docker=use_docker)
    content_graph_builder = ContentGraphBuilder(REPO_PATH, NEO4J_INTERFACE, clean_graph=False)
    logger.info('Content Graph was loaded')
    return content_graph_builder.content_graph


def stop_content_graph(
    use_docker: bool = True,
) -> None:
    """
    This function stops the neo4j service if it is running.
    """
    neo4j_service.stop_neo4j_service(use_docker=use_docker)


def marshal_content_graph(marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR) -> Repository:    
    """This function marshals the content graph to python models.

    Args:
        marketplace (MarketplaceVersions, optional): The marketplace to use. Defaults to MarketplaceVersions.XSOAR.
    
    Returns:
        Repository: The repository model loaded from the content graph.

    """
    content_graph_loader = ContentGraphLoader(marketplace, NEO4J_INTERFACE)
    return content_graph_loader.load()
