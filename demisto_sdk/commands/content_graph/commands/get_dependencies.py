from pathlib import Path
from typing import Any, Dict, Optional

import typer
from tabulate import tabulate

from demisto_sdk.commands.common.constants import PACKS_DIR, MarketplaceVersions
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import (
    logger,
    logging_setup,
)
from demisto_sdk.commands.content_graph.commands.get_relationships import (
    Direction,
    format_record_for_outputs,
    log_record,
)
from demisto_sdk.commands.content_graph.commands.update import update_content_graph
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.interface import ContentGraphInterface
from demisto_sdk.commands.content_graph.interface.neo4j.queries.dependencies import (
    MAX_DEPTH,
)

app = typer.Typer()


COMMAND_OUTPUTS_FILENAME = "get_dependencies_outputs.json"


@app.command(
    no_args_is_help=True,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def get_dependencies(
    ctx: typer.Context,
    input: str = typer.Argument(
        ...,
        help="The ID of the pack to check dependencies for.",
    ),
    update_graph: bool = typer.Option(
        True,
        "-u/-nu",
        "--update-graph/--no-update-graph",
        is_flag=True,
        help="If true, runs an update on the graph before querying.",
    ),
    marketplace: MarketplaceVersions = typer.Option(
        MarketplaceVersions.XSOAR,
        "-mp",
        "--marketplace",
        show_default=True,
        case_sensitive=False,
        help="The marketplace version.",
    ),
    mandatory_only: bool = typer.Option(
        False,
        "--mandatory-only",
        is_flag=True,
        help="If true, returns only mandatory dependencies.",
    ),
    all_level_dependencies: bool = typer.Option(
        True,
        "--all-level-deps/--first-level-deps",
        is_flag=True,
        help="Whether or not to retrieve all level or first level of dependencies only, default is all.",
    ),
    include_tests: bool = typer.Option(
        False,
        "--incude-test-dependencies",
        is_flag=True,
        help="If true, includes tests dependencies in outputs.",
    ),
    include_deprecated: bool = typer.Option(
        False,
        "--include-deprecated",
        is_flag=True,
        help="If true, includes deprecated in outputs.",
    ),
    include_hidden: bool = typer.Option(
        False,
        "--include-hidden",
        is_flag=True,
        help="If true, includes hidden packs in outputs.",
    ),
    direction: Direction = typer.Option(
        Direction.TARGETS,
        "-dir",
        "--direction",
        show_default=True,
        case_sensitive=False,
        help="Specifies whether to return only dependents (sources), only dependencies (targets) or both.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "-o",
        "--output",
        exists=True,
        dir_okay=True,
        resolve_path=True,
        show_default=False,
        help="A path to a directory in which to dump the outputs to.",
    ),
    console_log_threshold: str = typer.Option(
        "INFO",
        "-clt",
        "--console_log_threshold",
        help=("Minimum logging threshold for the console logger."),
    ),
    file_log_threshold: str = typer.Option(
        "DEBUG",
        "-flt",
        "--file_log_threshold",
        help=("Minimum logging threshold for the file logger."),
    ),
    log_file_path: str = typer.Option(
        "demisto_sdk_debug.log",
        "-lp",
        "--log_file_path",
        help=("Path to the log file. Default: ./demisto_sdk_debug.log."),
    ),
) -> None:
    """
    Returns dependencies of a given content pack.
    """
    logging_setup(
        console_log_threshold=console_log_threshold,
        file_log_threshold=file_log_threshold,
        log_file_path=log_file_path,
    )
    with ContentGraphInterface() as graph:
        if update_graph:
            update_content_graph(graph)
        result = get_dependencies_by_pack_path(
            graph,
            input,
            all_level_dependencies,
            marketplace,
            direction,
            mandatory_only,
            include_tests,
            include_deprecated,
            include_hidden,
        )
        if output:
            (output / COMMAND_OUTPUTS_FILENAME).write_text(
                json.dumps(result, indent=4),
            )


def get_dependencies_by_pack_path(
    graph: ContentGraphInterface,
    pack_id: str,
    all_level_dependencies: bool,
    marketplace: MarketplaceVersions,
    direction: Direction,
    mandatory_only: bool,
    include_tests: bool,
    include_deprecated: bool,
    include_hidden: bool,
) -> Dict[str, Any]:
    pack_path: Path = Path(PACKS_DIR) / pack_id
    depth: int = MAX_DEPTH if all_level_dependencies else 1
    retrieve_sources: bool = direction != Direction.TARGETS
    retrieve_targets: bool = direction != Direction.SOURCES

    dependents, dependencies = graph.get_relationships_by_path(
        pack_path,
        RelationshipType.DEPENDS_ON,
        ContentType.PACK,
        depth,
        marketplace,
        retrieve_sources,
        retrieve_targets,
        mandatory_only,
        include_tests,
        include_deprecated,
        include_hidden,
    )
    for record in dependents + dependencies:
        log_record(record, RelationshipType.DEPENDS_ON)
        format_record_for_outputs(record, RelationshipType.DEPENDS_ON)
    logger.info("[cyan]====== SUMMARY ======[/cyan]")
    if retrieve_sources:
        logger.info(f"Dependents:\n{to_tabulate(dependents)}\n")
    if retrieve_targets:
        logger.info(f"Dependencies:\n{to_tabulate(dependencies)}\n")
    return {"dependents": dependents, "dependencies": dependencies}


def to_tabulate(
    data: list,
) -> str:
    if not data:
        return "No results."

    headers = ["Pack", "Mandatory", "Depth"]
    fieldnames_to_collect = ["name", "mandatorily", "minDepth"]
    maxcolwidths = [50] * len(headers)

    tabulated_data = []
    for record in data:
        tabulated_data.append([record[f] for f in fieldnames_to_collect])

    return tabulate(
        tabulated_data,
        headers=headers,
        tablefmt="fancy_grid",
        maxcolwidths=maxcolwidths,
    )
