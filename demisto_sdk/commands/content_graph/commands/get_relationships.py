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


class Direction(str, Enum):
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
        ContentType.BASE_NODE,
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
        help="Maximum depth (length) of the relationships paths.",
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
        "--include-tests",
        is_flag=True,
        help="If true, includes tests in outputs (relevant only for DEPENDS_ON/USES relationships).",
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
        help="If true, includes hidden packs in outputs (relevant only for DEPENDS_ON relationships).",
    ),
    direction: Direction = typer.Option(
        Direction.BOTH,
        "-dir",
        "--direction",
        show_default=True,
        case_sensitive=False,
        help="Specifies whether to return only sources, only targets or both.",
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
    Returns relationships of a given content object.
    """
    logging_setup(
        console_log_threshold=console_log_threshold,
        file_log_threshold=file_log_threshold,
        log_file_path=log_file_path,
    )
    if relationship == RelationshipType.HAS_COMMAND:
        raise ValueError(
            f"Searching relationships of type {relationship} is not supported for this command."
            "To find which integrations implement specific commands, please run "
            "`demisto-sdk graph get-command-usage <COMMAND_NAME>`"
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
            include_deprecated,
            include_hidden,
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
    include_deprecated: bool,
    include_hidden: bool,
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
        include_deprecated,
        include_hidden,
    )
    for record in sources + targets:
        log_record(record, relationship)
        format_record_for_outputs(record, relationship)
    logger.info("[cyan]====== SUMMARY ======[/cyan]")
    if retrieve_sources:
        logger.info(f"Sources:\n{to_tabulate(sources)}\n")
    if retrieve_targets:
        logger.info(f"Targets:\n{to_tabulate(targets)}\n")
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
    def node_to_str(node_data: dict) -> str:
        name = f"[cyan]{node_data['name']}[/cyan]"
        content_type = f"[lightblue]{node_data['content_type']}[/lightblue]"
        path = node_data["path"]
        return f"• ({name}:{content_type} {{path: {path}}})\n"

    def rel_to_str(rel: RelationshipType, props: dict) -> str:
        return f"   └─ [[purple]{rel}[/purple]]{props or ''} ↴\n"

    path_str = ""
    for idx, path_element in enumerate(path):
        if idx % 2 == 0:
            path_str += node_to_str(path_element)
        else:
            path_str += rel_to_str(relationship, path_element)
    return path_str


def format_record_for_outputs(
    record: Dict[str, Any],
    relationship: RelationshipType,
) -> None:
    del record["is_source"]  # unnecessary field in output
    for path_data in record["paths"]:
        formatted_path = []
        for idx, path_element in enumerate(path_data["path"]):
            if idx % 2 == 0:
                formatted_path.append({f"node_{idx // 2}": path_element})
            else:
                formatted_path.append({relationship: path_element})
        path_data["path"] = formatted_path


def to_tabulate(
    data: list,
) -> str:
    if not data:
        return "No results."

    headers = ["Name", "Type", "Path", "Depth"]
    fieldnames_to_collect = ["name", "content_type", "filepath", "minDepth"]
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
