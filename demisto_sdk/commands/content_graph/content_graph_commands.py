import logging
import shutil
from pathlib import Path
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.content_graph_builder import \
    ContentGraphBuilder
from demisto_sdk.commands.content_graph.content_graph_loader import ContentGraphLoader
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.content_graph.common import REPO_PATH
from demisto_sdk.commands.content_graph.objects.repository import Repository

logger = logging.getLogger('demisto-sdk')


def create_content_graph(
    content_graph_interface: ContentGraphInterface,
    use_docker: bool = True,
    use_existing: bool = False,
    should_dump: bool = False,
) -> None:
    """This function creates a new content graph database in neo4j from the content path

    Args:
        use_docker (bool, optional): Whether run neo4j in docker. Defaults to True.
        use_existing (bool, optional): Whether use existing service. Defaults to False.
    """
    logger.info('Creating content graph')
    if not use_existing:
        shutil.rmtree(REPO_PATH / 'neo4j' / 'data', ignore_errors=True)
        neo4j_service.start_neo4j_service(use_docker)
    content_graph_builder = ContentGraphBuilder(REPO_PATH, content_graph_interface)
    content_graph_builder.create_graph()
    if should_dump:
        neo4j_service.dump(use_docker=use_docker)


def load_content_graph(
    content_graph_interface: ContentGraphInterface,
    use_docker: bool = True,
    content_graph_path: Path = None,
) -> None:
    """This function loads a database dump file to the content graph database in neo4j

    Args:
        use_docker (bool, optional): Whether run neo4j in docker. Defaults to True.
        content_graph_path (Path, optional): The dump file path to load from. Defaults to None, which means use the default path.
                                             Default path: (<REPO_PATH>/neo4j/backups/content-graph.dump)
    """
    if content_graph_path and content_graph_path.is_file():
        shutil.copy(content_graph_path, REPO_PATH / 'neo4j' / 'backups' / 'content-graph.dump')
    neo4j_service.load(use_docker=use_docker)
    ContentGraphBuilder(REPO_PATH, content_graph_interface, clean_graph=False)
    logger.info('Content Graph was loaded')


def stop_content_graph(
    use_docker: bool = True,
) -> None:
    """
    This function stops the neo4j service if it is running.
    """
    neo4j_service.stop_neo4j_service(use_docker=use_docker)


def marshal_content_graph(
    content_graph_interface: ContentGraphInterface,
    marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
    with_dependencies: bool = False,
) -> Repository:
    """This function marshals the content graph to python models.

    Args:
        marketplace (MarketplaceVersions, optional): The marketplace to use. Defaults to MarketplaceVersions.XSOAR.

    Returns:
        Repository: The repository model loaded from the content graph.

    """
    content_graph_loader = ContentGraphLoader(marketplace, content_graph_interface, with_dependencies)
    return content_graph_loader.load()
