import logging
import shutil
from pathlib import Path
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.content_graph_builder import \
    ContentGraphBuilder
from demisto_sdk.commands.content_graph.content_graph_loader import ContentGraphLoader
from demisto_sdk.commands.content_graph.interface.neo4j_graph import \
    Neo4jContentGraphInterface

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.content_graph.constants import (NEO4J_DATABASE_URL,
                                                          NEO4J_PASSWORD,
                                                          NEO4J_USERNAME,
                                                          REPO_PATH)
from demisto_sdk.commands.content_graph.objects.repository import Repository

logger = logging.getLogger('demisto-sdk')

neo4j_interface = Neo4jContentGraphInterface(NEO4J_DATABASE_URL, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))


def create_content_graph(use_docker: bool = True, keep_service: bool = False) -> Neo4jContentGraphInterface:
    shutil.rmtree(REPO_PATH / 'neo4j' / 'data', ignore_errors=True)
    neo4j_service.start_neo4j_service(use_docker)
    content_graph_builder = ContentGraphBuilder(REPO_PATH, neo4j_interface)
    content_graph_builder.create_graph()
    if not keep_service:
        neo4j_service.stop_neo4j_service(use_docker)
        neo4j_service.dump()
    return content_graph_builder.content_graph


def load_content_graph(use_docker: bool = True, keep_service: bool = False, content_graph_path: Path = None) -> Neo4jContentGraphInterface:
    if content_graph_path and content_graph_path.is_file():
        shutil.copy(content_graph_path, REPO_PATH / 'neo4j' / 'backups' / 'content-graph.dump')
    neo4j_service.load()
    neo4j_service.start_neo4j_service(use_docker)
    content_graph_builder = ContentGraphBuilder(REPO_PATH, neo4j_interface)
    logger.info('Content Graph was loaded')
    if not keep_service:
        neo4j_service.stop_neo4j_service(use_docker)
    return content_graph_builder.content_graph


def update_content_graph():
    pass


def delete_content_graph():
    pass


def backup_content_graph():
    pass


def restore_content_graph():
    pass


def load_db_to_models(keep_service: bool = False, marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR) -> Repository:
    content_graph_loader = ContentGraphLoader(marketplace, neo4j_interface)
    repo: Repository = content_graph_loader.load()
    if not keep_service:
        neo4j_service.stop_neo4j_service()
    return repo
