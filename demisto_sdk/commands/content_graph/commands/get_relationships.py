from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import typer
from tabulate import tabulate

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import (
    logger,
    logging_setup,
)
from demisto_sdk.commands.content_graph.commands.update import update_content_graph
from demisto_sdk.commands.content_graph.common import (
    ContentType,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.interface import ContentGraphInterface

app = typer.Typer()


COMMAND_OUTPUTS_FILENAME = "get_relationships_outputs.json"


class Direction(Enum):
    SOURCES = "sources"
    TARGETS = "targets"
    BOTH = "both"


@app.command(
    no_args_is_help=True,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def get_relationships(
    ctx: typer.Context,
    input: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=True,
        resolve_path=True,
        show_default=False,
        help="The path to a content item or a pack.",
    ),
    relationship: RelationshipType = typer.Option(
        RelationshipType.USES,
        "-r",
        "--relationship",
        show_default=True,
        case_sensitive=False,
        help="The type of relationships to inspect.",
    ),
    content_type: ContentType = typer.Option(
        ContentType.BASE_CONTENT,
        "-ct",
        "--content-type",
        show_default=True,
        case_sensitive=False,
        help="The content type of the related object.",
    ),
    depth: int = typer.Option(
        1,
        "-d",
        "--depth",
        min=1,
        max=5,
        show_default=True,
        help="Maximum depth of the relationships path in the graph.",
    ),
    output: Optional[Path] = typer.Option(
        Path("."),
        "-o",
        "--output",
        exists=True,
        dir_okay=True,
        resolve_path=True,
        show_default=False,
        help="A path to a directory in which to dump the outputs to.",
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
        help="If true, returns only mandatory relationships (relevant only for DEPENDS_ON/USES relationships).",
    ),
    include_tests: bool = typer.Option(
        False,
        "--incude-test-dependencies",
        is_flag=True,
        help="If true, includes tests dependencies in outputs (relevant only for DEPENDS_ON relationships).",
    ),
    direction: Direction = typer.Option(
        Direction.BOTH,
        "-dir",
        "--direction",
        show_default=True,
        case_sensitive=False,
        help="Specifies whether to return only sources, only targets or both.",
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
    Returns relationships of a given content object.
    """
    logging_setup(
        console_log_threshold=console_log_threshold,
        file_log_threshold=file_log_threshold,
        log_file_path=log_file_path,
    )
    with ContentGraphInterface() as graph:
        if update_graph:
            update_content_graph(graph)
        result = get_relationships_by_path(
            graph,
            input.relative_to(graph.repo_path),
            relationship,
            content_type,
            depth,
            marketplace,
            direction,
            mandatory_only,
            include_tests,
        )
        if output:
            (output / COMMAND_OUTPUTS_FILENAME).write_text(
                json.dumps(result, indent=4),
            )


def get_relationships_by_path(
    graph: ContentGraphInterface,
    input_filepath: Path,
    relationship: RelationshipType,
    content_type: ContentType,
    depth: int,
    marketplace: MarketplaceVersions,
    direction: Direction,
    mandatory_only: bool,
    include_tests: bool,
) -> Dict[str, Any]:
    retrieve_sources: bool = direction != Direction.TARGETS
    retrieve_targets: bool = direction != Direction.SOURCES

    sources, targets = graph.get_relationships_by_path(
        input_filepath,
        relationship,
        content_type,
        depth,
        marketplace,
        retrieve_sources,
        retrieve_targets,
        mandatory_only,
        include_tests,
    )
    for record in sources + targets:
        log_record(record, relationship)
    logger.info("[cyan]====== SUMMARY ======[/cyan]")
    if retrieve_sources:
        logger.info(f"Sources:\n{to_tabulate(sources, relationship)}\n")
    if retrieve_targets:
        logger.info(f"Targets:\n{to_tabulate(targets, relationship)}\n")
    return {"sources": sources, "targets": targets}


def log_record(
    record: Dict[str, Any],
    relationship: RelationshipType,
) -> None:
    is_source = record["is_source"]
    for path in record["paths"]:
        mandatorily = (
            f" (mandatory: {path['mandatorily']})"
            if path["mandatorily"] is not None
            else ""
        )
        logger.debug(
            f"[yellow]Found a {relationship} path{mandatorily}"
            f"{' from ' if is_source else ' to '}"
            f"{record['filepath']}[/yellow]\n"
            f"{path_to_str(relationship, path['path'])}\n"
        )


def path_to_str(
    relationship: RelationshipType,
    path: list,
) -> str:
    def node_to_str(path: str) -> str:
        return f"({path})"

    def rel_to_str(rel: RelationshipType, props: dict) -> str:
        rel_data = f"[{rel}{props or ''}]"
        spaces = " " * (len(rel_data) // 2 - 1)
        return f"\n{spaces}|\n{rel_data}\n{spaces}↓\n"

    path_str = ""
    for idx, path_element in enumerate(path):
        if idx % 2 == 0:
            path_str += node_to_str(path_element)
        else:
            path_str += rel_to_str(relationship, path_element)
    return path_str


def to_tabulate(
    data: list,
    relationship: RelationshipType,
) -> str:
    if not data:
        return "No results."

    headers = ["File Path", "Min Depth"]
    fieldnames_to_collect = ["filepath", "minDepth"]
    maxcolwidths = [70, None]
    if relationship in [RelationshipType.USES, RelationshipType.DEPENDS_ON]:
        headers.append("Mandatory")
        fieldnames_to_collect.append("mandatorily")
        maxcolwidths.append(None)

    tabulated_data = []
    for record in data:
        tabulated_data.append([record[f] for f in fieldnames_to_collect])

    return tabulate(
        tabulated_data,
        headers=headers,
        tablefmt="fancy_grid",
        maxcolwidths=maxcolwidths,
    )
