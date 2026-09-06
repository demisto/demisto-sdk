import os
from pathlib import Path
from typing import List, Optional, Set, Tuple

import typer

from demisto_sdk.commands.common.constants import (
    CONNECTORS_FOLDER,
    PACKS_FOLDER,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
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
from demisto_sdk.commands.validate.private_content_manager import (
    PrivateContentManager,
)

app = typer.Typer()

# Environment variable name for passing diff files list
DEMISTO_SDK_DIFF_FILES_ENV = "DEMISTO_SDK_DIFF_FILES"


def extract_pack_ids_from_diff_files(diff_files_str: str) -> Set[str]:
    """Extract unique pack IDs from a list of diff file paths.

    Args:
        diff_files_str: A string containing file paths, separated by spaces or newlines.
                       Example: "Packs/MyPack/file.py Packs/OtherPack/file.yml"

    Returns:
        A set of unique pack IDs extracted from the file paths.
    """
    if not diff_files_str:
        return set()

    # Support both space-separated and newline-separated file lists
    diff_files = diff_files_str.replace("\n", " ").split()

    pack_ids: Set[str] = set()
    for file_path in diff_files:
        path_parts = Path(file_path).parts
        # Check if the file is under Packs/ folder and has at least pack name
        if len(path_parts) > 1 and path_parts[0] == PACKS_FOLDER:
            pack_ids.add(path_parts[1])

    return pack_ids


def extract_connector_ids_from_diff_files(diff_files_str: str) -> Set[str]:
    """Extract unique connector directory names from a list of diff file paths.

    Connectors live at the repo root under ``connectors/<connector-name>/...``
    (outside of ``Packs/``), so we look for paths whose first segment is
    ``connectors``.

    Args:
        diff_files_str: A string containing file paths, separated by spaces or
            newlines. Example:
            ``"connectors/salesforce/connector.yaml connectors/okta/handler.yaml"``

    Returns:
        A set of unique connector directory names extracted from the file paths.
    """
    if not diff_files_str:
        return set()

    diff_files = diff_files_str.replace("\n", " ").split()

    connector_ids: Set[str] = set()
    for file_path in diff_files:
        path_parts = Path(file_path).parts
        if len(path_parts) > 1 and path_parts[0] == CONNECTORS_FOLDER:
            connector_ids.add(path_parts[1])

    return connector_ids


def _changed_connectors_from_git(git_util: GitUtil, commit: str) -> Set[str]:
    """Return connector directory names touched between ``commit`` and HEAD.

    Uses the same diff machinery as
    :py:meth:`GitUtil.get_all_changed_pack_ids`, but filters for the
    ``connectors/`` prefix. Always returns a set (never raises) so callers
    can treat it as best-effort; failures are logged at warning level since
    a silent miss means the graph drops connector updates.
    """
    # Skip the git scan (and its noisy warning) when the connectors folder
    # isn't present in this checkout - e.g. the run-validations CI job which
    # doesn't copy connectors in. Connector diffing only matters when the
    # folder actually exists locally.
    if not (CONTENT_PATH / CONNECTORS_FOLDER).is_dir():
        return set()

    try:
        # GitUtil.get_all_changed_files returns Set[Path] of changed paths
        # relative to the repo root.
        changed_files = git_util.get_all_changed_files(commit)
    except Exception as e:
        logger.warning(f"Could not enumerate changed files for connectors: {e}")
        return set()

    connector_ids: Set[str] = set()
    for file_path in changed_files:
        parts = Path(file_path).parts
        if len(parts) > 1 and parts[0] == CONNECTORS_FOLDER:
            connector_ids.add(parts[1])
    return connector_ids


def should_update_graph(
    content_graph_interface: ContentGraphInterface,
    use_git: bool,
    git_util: GitUtil,
    imported_path: Optional[Path] = None,
    packs_to_update: Optional[List[str]] = None,
    connectors_to_update: Optional[List[str]] = None,
    changed_pack_ids: Optional[Set[str]] = None,
    changed_connector_ids: Optional[Set[str]] = None,
):
    """Decide whether the graph needs to be (re)built.

    Args:
        changed_pack_ids: Pre-computed set of pack ids changed since the
            graph's pinned commit. When provided, the caller has already
            done the git work and we reuse it. When ``None``, this function
            computes it from git (legacy behaviour). Pass the empty set to
            assert "no changed packs" without triggering a git scan.
        changed_connector_ids: Same as above for connectors.
    """
    if content_graph_interface.commit and (
        changed_pack_ids is None or changed_connector_ids is None
    ):
        # No caller-provided diff results - fall back to scanning git ourselves
        # so legacy callers (and tests) keep working without changes.
        try:
            if changed_pack_ids is None:
                changed_pack_ids = git_util.get_all_changed_pack_ids(
                    content_graph_interface.commit
                )
        except Exception:
            logger.debug(
                "Failed to get changed packs from git. Setting to update graph."
            )
            # If we can't get the changed packs, it could mean the following:
            # 1. We are not fetched from a git repository and unable to fetch
            # 2. The current graph that is running is not in the same repo as we run now
            # 3. The graph which is running is a graph that was created from unit-testing
            # Anyway, we cannot trust the current graph, so we need to update it.
            return True
        if changed_connector_ids is None:
            # Best-effort: _changed_connectors_from_git never raises.
            changed_connector_ids = _changed_connectors_from_git(
                git_util, content_graph_interface.commit
            )
    # Normalise to empty sets so the ``any(...)`` checks below never see None.
    changed_pack_ids = changed_pack_ids or set()
    changed_connector_ids = changed_connector_ids or set()
    return any(
        (
            not content_graph_interface.is_alive(),  # if neo4j service is not alive, we need to update
            imported_path,  # if there is an imported path to import from, we need to update
            packs_to_update,  # if there are packs to update, we need to update
            connectors_to_update,  # if there are connectors to update, we need to update
            use_git
            and content_graph_interface.commit
            and changed_pack_ids,  # if there are any changed packs and we are using git, we need to update
            use_git
            and content_graph_interface.commit
            and changed_connector_ids,  # if there are any changed connectors and we are using git, we need to update
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
    connectors_to_update: Optional[List[str]] = None,
    dependencies: bool = True,
    output_path: Optional[Path] = None,
    private_content_path: Optional[Path] = None,
    create_graph_from_scratch: bool = False,
) -> None:
    """This function updates a new content graph database in neo4j from the content path
    Args:
        content_graph_interface (ContentGraphInterface): The content graph interface.
        marketplace (MarketplaceVersions): The marketplace to update.
        use_git (bool): Whether to use git to get the packs to update.
        imported_path (Path): The path to the imported graph.
        packs_to_update (List[str]): The packs to update.
        connectors_to_update (List[str]): Connector directory names (under
            ``connectors/``) to refresh in the graph. Connectors are top-level
            content items that live outside ``Packs/``.
        dependencies (bool): Whether to create the dependencies.
        output_path (Path): The path to export the graph zip to.
        private_content_path (Path): Path to the private content repository. When provided,
            private content packs will be temporarily copied to the content repository.
        create_graph_from_scratch (bool): Whether to create the graph from scratch instead of downloading.
    """
    # If private content path is provided, wrap the entire update in PrivateContentManager
    if private_content_path:
        logger.info(
            f"Private content path provided: {private_content_path}. "
            "Private content will be temporarily synced for graph update."
        )
        with PrivateContentManager(
            private_content_path=private_content_path,
            content_path=CONTENT_PATH,
        ):
            _update_content_graph_inner(
                content_graph_interface=content_graph_interface,
                marketplace=marketplace,
                use_git=use_git,
                imported_path=imported_path,
                packs_to_update=packs_to_update,
                connectors_to_update=connectors_to_update,
                dependencies=dependencies,
                output_path=output_path,
                create_graph_from_scratch=create_graph_from_scratch,
            )
        return

    _update_content_graph_inner(
        content_graph_interface=content_graph_interface,
        marketplace=marketplace,
        use_git=use_git,
        imported_path=imported_path,
        packs_to_update=packs_to_update,
        connectors_to_update=connectors_to_update,
        dependencies=dependencies,
        output_path=output_path,
        create_graph_from_scratch=create_graph_from_scratch,
    )


def _update_content_graph_inner(
    content_graph_interface: ContentGraphInterface,
    marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
    use_git: bool = False,
    imported_path: Optional[Path] = None,
    packs_to_update: Optional[List[str]] = None,
    connectors_to_update: Optional[List[str]] = None,
    dependencies: bool = True,
    output_path: Optional[Path] = None,
    create_graph_from_scratch: bool = False,
) -> None:
    """Internal function that performs the actual graph update logic.

    This is separated from update_content_graph to allow wrapping with PrivateContentManager
    when private_content_path is provided.
    """
    force_create_graph = os.getenv("DEMISTO_SDK_GRAPH_FORCE_CREATE")
    logger.debug(f"DEMISTO_SDK_GRAPH_FORCE_CREATE = {force_create_graph}")

    if string_to_bool(force_create_graph, False) or create_graph_from_scratch:
        logger.info("Will create a new graph from scratch")
        create_content_graph(
            content_graph_interface, marketplace, dependencies, output_path
        )
        return

    if (
        not imported_path
        and not use_git
        and not packs_to_update
        and not connectors_to_update
    ):
        logger.info("A path to import the graph from was not provided, using git")
        use_git = True

    git_util = GitUtil()
    is_external_repo = is_external_repository()

    if is_external_repo:
        packs_to_update = get_all_repo_pack_ids()
    packs_to_update = list(packs_to_update) if packs_to_update else []
    connectors_to_update = list(connectors_to_update) if connectors_to_update else []

    # Check for diff files from environment variable
    # This allows CI systems to pass a list of changed files directly,
    # bypassing git-based detection which may not work in all CI environments.
    # Track whether the changed-items list came from an explicit, trusted source
    # (caller-supplied args or DEMISTO_SDK_DIFF_FILES). When it did, we must NOT
    # fall back to git-diff augmentation later - in CI the graph's pinned commit
    # is often absent from the local history (shallow clone) and `git diff`
    # fails, which currently tears down the whole import via "Creating from
    # scratch". The env-var path is the single source of truth in that case.
    explicit_changes_provided = bool(packs_to_update or connectors_to_update)

    # Read env var if either list is still empty - the two are independent so a
    # caller that passed --packs only should still pick up connector entries
    # from DEMISTO_SDK_DIFF_FILES (and vice versa).
    if not packs_to_update or not connectors_to_update:
        diff_files_env = os.getenv(DEMISTO_SDK_DIFF_FILES_ENV, "")
        if diff_files_env:
            if not packs_to_update:
                env_pack_ids = extract_pack_ids_from_diff_files(diff_files_env)
                if env_pack_ids:
                    logger.info(
                        f"Extracted {len(env_pack_ids)} pack IDs from {DEMISTO_SDK_DIFF_FILES_ENV} "
                        f"environment variable: {sorted(env_pack_ids)}"
                    )
                    packs_to_update.extend(env_pack_ids)
                    explicit_changes_provided = True
            if not connectors_to_update:
                env_connector_ids = extract_connector_ids_from_diff_files(
                    diff_files_env
                )
                if env_connector_ids:
                    logger.info(
                        f"Extracted {len(env_connector_ids)} connector IDs from "
                        f"{DEMISTO_SDK_DIFF_FILES_ENV} environment variable: "
                        f"{sorted(env_connector_ids)}"
                    )
                    connectors_to_update.extend(env_connector_ids)
                    explicit_changes_provided = True

    builder = ContentGraphBuilder(content_graph_interface)
    if not should_update_graph(
        content_graph_interface,
        use_git,
        git_util,
        imported_path,
        packs_to_update,
        connectors_to_update,
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
    # Compute changed packs/connectors via git-diff now that the graph has
    # been imported and ``content_graph_interface.commit`` is populated with
    # the bucket's pinned commit. When the caller (or DEMISTO_SDK_DIFF_FILES)
    # already provided an explicit list, skip the git diff - in shallow CI
    # clones the bucket commit is often absent and ``git diff`` would fail,
    # which would incorrectly tear down the whole import via "creating from
    # scratch".
    if (
        use_git
        and (commit := content_graph_interface.commit)
        and not is_external_repo
        and not explicit_changes_provided
    ):
        try:
            changed_pack_ids = git_util.get_all_changed_pack_ids(commit)
        except Exception as e:
            logger.warning(
                f"Failed to get changed packs from git. Creating from scratch. Error: {e}"
            )
            create_content_graph(
                content_graph_interface, marketplace, dependencies, output_path
            )
            return
        packs_to_update.extend(changed_pack_ids)
        # Best-effort: _changed_connectors_from_git never raises.
        connectors_to_update.extend(_changed_connectors_from_git(git_util, commit))
    elif explicit_changes_provided and use_git:
        logger.info(
            "Skipping git-diff augmentation: changed packs/connectors were "
            "provided explicitly (via caller args or "
            f"{DEMISTO_SDK_DIFF_FILES_ENV}), so the bucket-commit git diff "
            "is redundant and would fail in shallow CI clones."
        )

    if packs_to_update:
        packs_str = "\n".join([f"- {p}" for p in sorted(packs_to_update)])
        logger.info(f"Updating the following packs:\n{packs_str}")
    if connectors_to_update:
        connectors_str = "\n".join([f"- {c}" for c in sorted(connectors_to_update)])
        logger.info(f"Updating the following connectors:\n{connectors_str}")

    # Deduplicate before passing to the builder - git diffs may report the
    # same pack/connector multiple times across modified/added/renamed buckets.
    packs_tuple: Optional[Tuple[str, ...]] = (
        tuple(sorted(set(packs_to_update))) if packs_to_update else None
    )
    connectors_tuple: Optional[Tuple[str, ...]] = (
        tuple(sorted(set(connectors_to_update))) if connectors_to_update else None
    )
    builder.update_graph(
        packs_to_update=packs_tuple,
        connectors_to_update=connectors_tuple,
    )

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
    connectors_to_update: Optional[List[str]] = typer.Option(
        None,
        "-c",
        "--connectors",
        help=(
            "A comma-separated list of connectors (directory names under "
            "`connectors/`) to update. Connectors are top-level content items "
            "that live outside `Packs/`."
        ),
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
    private_content_path: Optional[Path] = typer.Option(
        None,
        "-pcp",
        "--private-content-path",
        exists=True,
        dir_okay=True,
        file_okay=False,
        resolve_path=True,
        help="Path to the private content repository. When provided, private content packs will be temporarily copied to the content repository for graph update.",
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
            connectors_to_update=(
                list(connectors_to_update) if connectors_to_update else []
            ),
            dependencies=not no_dependencies,
            output_path=output_path,
            private_content_path=private_content_path,
        )
