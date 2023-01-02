import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Optional

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.tools import (
    download_content_graph,
    get_latest_upload_flow_commit_hash,
)
from demisto_sdk.commands.content_graph.content_graph_builder import ContentGraphBuilder
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface

logger = logging.getLogger("demisto-sdk")


def create_content_graph(
    content_graph_interface: ContentGraphInterface,
    marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
    dependencies: bool = True,
    output_path: Optional[Path] = None,
) -> None:
    """This function creates a new content graph database in neo4j from the content path

    Args:
        content_graph_interface (ContentGraphInterface): The content graph interface.
        marketplace (MarketplaceVersions): The marketplace to update.
        dependencies (bool): Whether to create the dependencies.
        output_path (Path): The path to export the graph zip to.
    """
    ContentGraphBuilder(content_graph_interface).create_graph()
    if dependencies:
        content_graph_interface.create_pack_dependencies()
    if output_path:
        output_path = output_path / marketplace.value
    content_graph_interface.export_graph(output_path)


def update_content_graph(
    content_graph_interface: ContentGraphInterface,
    marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
    use_git: bool = False,
    imported_path: Optional[Path] = None,
    packs_to_update: Optional[List[str]] = None,
    dependencies: bool = True,
    output_path: Optional[Path] = None,
) -> None:
    """This function creates a new content graph database in neo4j from the content path
    Args:
        content_graph_interface (ContentGraphInterface): The content graph interface.
        marketplace (MarketplaceVersions): The marketplace to update.
        use_git (bool): Whether to use git to get the packs to update.
        imported_path (Path): The path to the imported graph.
        packs_to_update (List[str]): The packs to update.
        dependencies (bool): Whether to create the dependencies.
        output_path (Path): The path to export the graph zip to.
    """
    if use_git and imported_path:
        raise ValueError("Cannot use both git and imported path")
    if packs_to_update is None and not imported_path:
        # If no arguments were given, we will use the git diff to get the packs to update
        use_git = True

    if packs_to_update is None:
        packs_to_update = []
    builder = ContentGraphBuilder(content_graph_interface)

    if use_git:
        get_or_create_graph(content_graph_interface, builder)
        latest_commit = get_latest_upload_flow_commit_hash()
        packs_to_update.extend(GitUtil().get_all_changed_pack_ids(latest_commit))
    else:
        content_graph_interface.import_graph(imported_path)
    logger.info(f"Updating the following packs: {packs_to_update}")
    builder.update_graph(packs_to_update)
    if dependencies:
        content_graph_interface.create_pack_dependencies()
    if output_path:
        output_path = output_path / marketplace.value
    content_graph_interface.export_graph(output_path)


def get_or_create_graph(
    content_graph_interface: ContentGraphInterface, builder: ContentGraphBuilder
):
    try:
        with NamedTemporaryFile() as temp_file:
            official_content_graph = download_content_graph(Path(temp_file.name))
            content_graph_interface.import_graph(official_content_graph)
    except Exception as e:
        logger.info("Failed to download from bucket. Will create a new graph")
        logger.debug(f"Error: {e}")
        builder.create_graph()


def stop_content_graph() -> None:
    """
    This function stops the neo4j service if it is running.
    """
    neo4j_service.stop()
