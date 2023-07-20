from pathlib import Path
from typing import Any, Dict, Tuple

import typer

from demisto_sdk.commands.common.logger import (
    logger,
    logging_setup,
)
from demisto_sdk.commands.content_graph.common import (
    RelationshipType,
)
from demisto_sdk.commands.content_graph.interface import ContentGraphInterface

app = typer.Typer()


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
    depth: int = typer.Option(
        1,
        "-d",
        "--depth",
        min=1,
        max=5,
        show_default=True,
        help="Maximum depth of the relationships path in the graph.",
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
        sources, targets = get_relationships_by_path(
            graph,
            input.relative_to(graph.repo_path),
            relationship,
            depth,
        )
        log_outputs(relationship, sources, targets)


def add_source_record(
    sources: Dict[str, Any],
    record: Dict[str, Any],
) -> None:
    source_filepath = record["source_filepath"]
    sources.setdefault(source_filepath, {}).setdefault("paths", []).append(
        {
            "depth": record["depth"],
            "path": record["path"],
        }
    )
    if (mandatorily := record["mandatorily"]) is not None:
        sources[source_filepath]["mandatorily"] = (
            sources[source_filepath].get("mandatorily") or mandatorily
        )


def add_target_record(
    targets: Dict[str, Any],
    record: Dict[str, Any],
) -> None:
    target_filepath = record["target_filepath"]
    targets.setdefault(target_filepath, {}).setdefault("paths", []).append(
        {
            "depth": record["depth"],
            "path": record["path"],
        }
    )
    if (mandatorily := record["mandatorily"]) is not None:
        targets[target_filepath]["mandatorily"] = (
            targets[target_filepath].get("mandatorily") or mandatorily
        )


def get_relationships_by_path(
    graph: ContentGraphInterface,
    path: Path,
    relationship: RelationshipType,
    depth: int,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    sources: Dict[str, Any] = {}
    targets: Dict[str, Any] = {}
    sources_data, targets_data = graph.get_relationships_by_path(
        path,
        relationship,
        depth,
    )
    for record in sources_data:
        add_source_record(sources, record)
    for record in targets_data:
        add_target_record(targets, record)
    return sources, targets


def log_single_path(
    relationship: RelationshipType,
    path: list,
) -> None:
    path_str = ""
    for idx, path_element in enumerate(path):
        if idx % 2 == 0:
            path_str += f"({path_element})"
        else:
            rel_data = f"[{relationship}{path_element or ''}]"
            spaces = " " * (len(rel_data) // 2 - 1)
            path_str += f"\n{spaces}|\n"
            path_str += f"{rel_data}\n"
            path_str += f"{spaces}↓\n"
    logger.info(f"\n{path_str}\n")


def log_single_source_or_target(
    source_or_target_filepath: str,
    is_source: bool,
    relationship: RelationshipType,
    source_or_target_data: Dict[str, Any],
) -> None:
    logger.info(
        f"[cyan]====== {'SOURCES' if is_source else 'TARGETS'} "
        f"(RELATIONSHIP TYPE: {relationship}) ======\n[/cyan]"
    )
    if not source_or_target_data:
        logger.info(
            f"[yellow]No {relationship} {'sources' if is_source else 'targets'} found.[/yellow]"
        )
    else:
        if (is_mandatory := source_or_target_data.get("mandatorily")) is not None:
            mandatory_info = f" (mandatory: {is_mandatory})"
        logger.info(
            f"[yellow]Found {len(source_or_target_data['paths'])} {relationship} path(s) "
            f"{'from source' if is_source else 'to target'} "
            f"{source_or_target_filepath}{mandatory_info}[/yellow]"
        )
        for path_data in source_or_target_data["paths"]:
            log_single_path(relationship, path_data["path"])


def log_summary(
    sources: Dict[str, Any],
    targets: Dict[str, Any],
) -> None:
    if sources or targets:
        logger.info("[cyan]====== SUMMARY ======[/cyan]")
        log: str = ""
        for filepath, data in sources.items():
            log += f"\n- {filepath}"
            if (is_mandatory := data.get("mandatorily")) is not None:
                log += f" (mandatory: {is_mandatory})"
        if log:
            logger.info(f"Sources:[green]{log}[/green]")

        log = ""
        for filepath, data in targets.items():
            log += f"\n- {filepath}"
            if (is_mandatory := data.get("mandatorily")) is not None:
                log += f" (mandatory: {is_mandatory})"
        if log:
            logger.info(f"Targets:[green]{log}[/green]")


def log_outputs(
    relationship: RelationshipType,
    sources: Dict[str, Any],
    targets: Dict[str, Any],
) -> None:
    for source_filepath, source_data in sources.items():
        log_single_source_or_target(source_filepath, True, relationship, source_data)
    for target_filepath, target_data in targets.items():
        log_single_source_or_target(target_filepath, False, relationship, target_data)
    log_summary(sources, targets)
