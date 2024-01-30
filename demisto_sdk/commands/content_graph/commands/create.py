from pathlib import Path
from typing import Optional

import typer

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.common.logger import (
    logger,
    logging_setup,
)
from demisto_sdk.commands.content_graph.commands.common import recover_if_fails
from demisto_sdk.commands.content_graph.common import (
    NEO4J_DATABASE_HTTP,
    NEO4J_PASSWORD,
    NEO4J_USERNAME,
)
from demisto_sdk.commands.content_graph.content_graph_builder import (
    ContentGraphBuilder,
)
from demisto_sdk.commands.content_graph.interface import ContentGraphInterface

app = typer.Typer()


@recover_if_fails
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
    builder = ContentGraphBuilder(content_graph_interface)
    builder.init_database()
    builder.create_graph()
    if dependencies:
        content_graph_interface.create_pack_dependencies()
    content_graph_interface.export_graph(
        output_path, override_commit=True, marketplace=marketplace
    )
    logger.info(
        f"Successfully created the content graph. UI representation "
        f"is available at {NEO4J_DATABASE_HTTP} "
        f"(username: {NEO4J_USERNAME}, password: {NEO4J_PASSWORD})"
    )


@app.command(
    no_args_is_help=True,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def create(
    ctx: typer.Context,
    marketplace: MarketplaceVersions = typer.Option(
        MarketplaceVersions.XSOAR,
        "-mp",
        "--marketplace",
        help="The marketplace to generate the graph for.",
    ),
    no_dependencies: bool = typer.Option(
        False,
        "-nd",
        "--no-dependencies",
        is_flag=True,
        help="Whether or not to include dependencies in the graph.",
    ),
    output_path: Path = typer.Option(
        None,
        exists=True,
        dir_okay=True,
        file_okay=False,
        resolve_path=True,
        help="Output folder to locate the zip file of the graph exported file.",
    ),
    console_log_threshold: str = typer.Option(
        "INFO",
        "-clt",
        "--console-log-threshold",
        help="Minimum logging threshold for the console logger.",
    ),
    file_log_threshold: str = typer.Option(
        "DEBUG",
        "-flt",
        "--file-log-threshold",
        help="Minimum logging threshold for the file logger.",
    ),
    log_file_path: Optional[str] = typer.Option(
        None,
        "-lp",
        "--log-file-path",
        help="Path to save log files onto.",
    ),
) -> None:
    """
    Parses all content packs under the repository, including their
    relationships. Then, the parsed content objects are mapped to
    a Repository model and uploaded to the graph database.
    """
    logging_setup(
        console_log_threshold=console_log_threshold,
        file_log_threshold=file_log_threshold,
        log_file_path=log_file_path,
    )
    with ContentGraphInterface() as content_graph_interface:
        create_content_graph(
            content_graph_interface=content_graph_interface,
            marketplace=marketplace,
            dependencies=not no_dependencies,
            output_path=output_path,
        )


def stop_content_graph() -> None:
    """
    This function stops the neo4j service if it is running.
    """
    neo4j_service.stop()
