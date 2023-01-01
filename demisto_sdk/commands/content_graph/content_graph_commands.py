import logging
from pathlib import Path
from tempfile import TemporaryFile
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
    export: bool = False,
    output_path: Optional[Path] = None,
) -> None:
    """This function creates a new content graph database in neo4j from the content path

    Args:
        content_graph_interface (ContentGraphInterface): The content graph interface.
    """
    ContentGraphBuilder(content_graph_interface).create_graph()
    if dependencies:
        content_graph_interface.create_pack_dependencies()
    if output_path:
        output_path = output_path / f"{marketplace.value}.zip"
    if export:
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
    """
    if use_git and imported_path:
        raise ValueError("Cannot use both git and imported path")
    builder = ContentGraphBuilder(content_graph_interface)
    if not packs_to_update and not imported_path:
        # If no arguments were given, we will use the git diff to get the packs to update
        use_git = True

    if use_git:
        try:
            with TemporaryFile() as temp_file:
                download_content_graph(Path(temp_file.name))
                # TODO return filepath of the downloaded file
                content_graph_interface.import_graph(
                    Path(temp_file.name) / f"{marketplace.value}.zip"
                )

            latest_commit = get_latest_upload_flow_commit_hash()
            # TODO - add to current list
            packs_to_update = list(GitUtil().get_all_changed_pack_ids(latest_commit))
        except Exception as e:
            logger.info("Failed to download from bucket. Will create a new graph")
            logger.debug(f"Error: {e}")
            builder.create_graph()
    if imported_path:
        content_graph_interface.import_graph(imported_path)
    logger.info(f"Updating the following packs: {packs_to_update}")
    builder.update_graph(packs_to_update)
    if dependencies:
        content_graph_interface.create_pack_dependencies()
    if output_path:
        output_path = output_path / f"{marketplace.value}.zip"
    content_graph_interface.export_graph(output_path)


def stop_content_graph() -> None:
    """
    This function stops the neo4j service if it is running.
    """
    neo4j_service.stop()
