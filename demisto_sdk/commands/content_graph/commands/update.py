import os
from pathlib import Path
from typing import List, Optional

import typer

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger, logging_setup
from demisto_sdk.commands.common.tools import (
    get_all_repo_pack_ids,
    is_external_repository,
    string_to_bool,
)
from demisto_sdk.commands.content_graph.commands.common import recover_if_fails
from demisto_sdk.commands.content_graph.commands.create import create_content_graph
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


def should_update_graph(
    content_graph_interface: ContentGraphInterface,
    use_git: bool,
    git_util: GitUtil,
    imported_path: Optional[Path] = None,
    packs_to_update: Optional[List[str]] = None,
):
    if content_graph_interface.commit:
        try:
            changed_pack_ids = git_util.get_all_changed_pack_ids(
                content_graph_interface.commit
            )
        except Exception:
            logger.debug(
                "Failed to get changed packs from git. Setting to update graph."
            )
            # If we can't get the changed packs, it could mean the followiing:
            # 1. We are not fetched from a git repository and unable to fetch
            # 2. The current graph that is running is not in the same repo as we run now
            # 3. The graph which is running is a graph that was created from unit-testing
            # Anyway, we cannot trust the current graph, so we need to update it.
            return True
    return any(
        (
            not content_graph_interface.is_alive(),  # if neo4j service is not alive, we need to update
            imported_path,  # if there is an imported path to import from, we need to update
            packs_to_update,  # if there are packs to update, we need to update
            use_git
            and content_graph_interface.commit
            and changed_pack_ids,  # if there are any changed packs and we are using git, we need to update
            content_graph_interface.content_parser_latest_hash
            != content_graph_interface._get_latest_content_parser_hash(),  # if the parse hash changed, we need to update
        )
    )


@recover_if_fails
def update_content_graph(
    content_graph_interface: ContentGraphInterface,
    marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
    use_git: bool = False,
    imported_path: Optional[Path] = None,
    packs_to_update: Optional[List[str]] = None,
    dependencies: bool = True,
    output_path: Optional[Path] = None,
) -> None:
    """This function updates a new content graph database in neo4j from the content path
    Args:
        content_graph_interface (ContentGraphInterface): The content graph interface.
        marketplace (MarketplaceVersions): The marketplace to update.
        use_git (bool): Whether to use git to get the packs to update.
        imported_path (Path): The path to the imported graph.
        packs_to_update (List[str]): The packs to update.
        dependencies (bool): Whether to create the dependencies.
        output_path (Path): The path to export the graph zip to.
    """
    force_create_graph = os.getenv("DEMISTO_SDK_GRAPH_FORCE_CREATE")
    logger.debug(f"DEMISTO_SDK_GRAPH_FORCE_CREATE = {force_create_graph}")

    if string_to_bool(force_create_graph, False):
        logger.info("DEMISTO_SDK_GRAPH_FORCE_CREATE is set. Will create a new graph")
        create_content_graph(
            content_graph_interface, marketplace, dependencies, output_path
        )
        return

    if not imported_path and not use_git:
        logger.info("A path to import the graph from was not provided, using git")
        use_git = True

    git_util = GitUtil()
    is_external_repo = is_external_repository()

    if is_external_repo:
        packs_to_update = get_all_repo_pack_ids()
    packs_to_update = list(packs_to_update) if packs_to_update else []
    builder = ContentGraphBuilder(content_graph_interface)
    if not should_update_graph(
        content_graph_interface, use_git, git_util, imported_path, packs_to_update
    ):
        logger.info(
            f"Content graph is up-to-date. If you expected an update, make sure your changes are added/committed to git. UI representation is available at {NEO4J_DATABASE_HTTP} "
            f"(username: {NEO4J_USERNAME}, password: {NEO4J_PASSWORD})"
        )
        content_graph_interface.export_graph(
            output_path,
            override_commit=use_git,
            marketplace=marketplace,
            clean_import_dir=False,
        )

        return
    builder.init_database()
    if imported_path:
        # Import from provided path
        content_graph_interface.import_graph(imported_path)

    else:
        # Try to import from local folder
        success_local = False
        if not is_external_repo:
            success_local = content_graph_interface.import_graph()

        if not success_local:
            builder.init_database()
            # Import from remote if local failed
            # If the download fails and we are in external repo, we should raise an error
            success_remote = content_graph_interface.import_graph(
                download=True, fail_on_error=is_external_repo
            )
            if not success_remote and not is_external_repo:
                logger.warning(
                    "Importing graph from bucket failed. Creating from scratch"
                )
                create_content_graph(
                    content_graph_interface, marketplace, dependencies, output_path
                )
                return
    if use_git and (commit := content_graph_interface.commit) and not is_external_repo:
        try:
            git_util.get_all_changed_pack_ids(commit)
        except Exception as e:
            logger.warning(
                f"Failed to get changed packs from git. Creating from scratch. Error: {e}"
            )
            create_content_graph(
                content_graph_interface, marketplace, dependencies, output_path
            )
            return
        packs_to_update.extend(git_util.get_all_changed_pack_ids(commit))

    packs_str = "\n".join([f"- {p}" for p in sorted(packs_to_update)])
    logger.info(f"Updating the following packs:\n{packs_str}")

    builder.update_graph(tuple(packs_to_update) if packs_to_update else None)

    if dependencies:
        content_graph_interface.create_pack_dependencies()
    content_graph_interface.export_graph(
        output_path, override_commit=use_git, marketplace=marketplace
    )
    logger.info(
        f"Successfully updated the content graph. UI representation is available at {NEO4J_DATABASE_HTTP} "
        f"(username: {NEO4J_USERNAME}, password: {NEO4J_PASSWORD})"
    )


@app.command(
    no_args_is_help=True,
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
        "help_option_names": ["-h", "--help"],
    },
)
def update(
    ctx: typer.Context,
    use_git: bool = typer.Option(
        False,
        "-g",
        "--use-git",
        is_flag=True,
        help="If true, uses git to determine the packs to update.",
    ),
    marketplace: MarketplaceVersions = typer.Option(
        MarketplaceVersions.XSOAR,
        "-mp",
        "--marketplace",
        help="The marketplace to generate the graph for.",
    ),
    imported_path: Path = typer.Option(
        None,
        "-i",
        "--imported-path",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
        help="Path to content graph zip file to import.",
    ),
    packs_to_update: Optional[List[str]] = typer.Option(
        None,
        "-p",
        "--packs",
        help="A comma-separated list of packs to update.",
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
        "-o",
        "--output-path",
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
    Downloads the official content graph, imports it locally,
    and updates it with the changes in the given repository
    or by an argument of packs to update with.
    """
    logging_setup(
        console_threshold=console_log_threshold,
        file_threshold=file_log_threshold,
        path=log_file_path,
        calling_function="graph update",
    )
    with ContentGraphInterface() as content_graph_interface:
        update_content_graph(
            content_graph_interface,
            marketplace=marketplace,
            use_git=use_git,
            imported_path=imported_path,
            packs_to_update=list(packs_to_update) if packs_to_update else [],
            dependencies=not no_dependencies,
            output_path=output_path,
        )
