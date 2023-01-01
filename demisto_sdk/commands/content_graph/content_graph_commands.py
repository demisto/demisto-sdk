import logging
from pathlib import Path
from typing import List, Optional
from zipfile import ZipFile

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.tools import get_latest_upload_flow_commit_hash
from demisto_sdk.commands.content_graph.content_graph_builder import ContentGraphBuilder
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface
from demisto_sdk.commands.content_graph.interface.neo4j.import_utils import (
    Neo4jImportHandler,
)

logger = logging.getLogger("demisto-sdk")


def create_content_graph(
    content_graph_interface: ContentGraphInterface,
    dependencies: bool = True,
    export: bool = False,
    output_file: Optional[Path] = None,
) -> None:
    """This function creates a new content graph database in neo4j from the content path

    Args:
        content_graph_interface (ContentGraphInterface): The content graph interface.
    """
    ContentGraphBuilder(content_graph_interface).create_graph()
    if dependencies:
        content_graph_interface.create_pack_dependencies()
    if export:
        content_graph_interface.export_graph(output_file)


def update_content_graph(
    content_graph_interface: ContentGraphInterface,
    use_git: bool = False,
    imported_path: Optional[Path] = None,
    packs_to_update: Optional[List[str]] = None,
    dependencies: bool = True,
    output_file: Optional[Path] = None,
) -> None:
    """This function creates a new content graph database in neo4j from the content path
    Args:
        content_graph_interface (ContentGraphInterface): The content graph interface.
    """
    import_handler = Neo4jImportHandler()

    if use_git and not packs_to_update and not imported_path:
        latest_commit = get_latest_upload_flow_commit_hash()
        packs_to_update = list(GitUtil().get_all_changed_pack_names(latest_commit))
        import_handler.download_from_bucket(import_handler.import_path)
    elif imported_path:
        with ZipFile(imported_path, "r") as zip_obj:
            zip_obj.extractall(import_handler.import_path)
    ContentGraphBuilder(content_graph_interface).update_graph(packs_to_update)
    if dependencies:
        content_graph_interface.create_pack_dependencies()
    content_graph_interface.export_graph(output_file)


def stop_content_graph() -> None:
    """
    This function stops the neo4j service if it is running.
    """
    neo4j_service.stop()
