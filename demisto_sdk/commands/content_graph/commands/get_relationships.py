from pathlib import Path
from typing import Any, Dict, List

import typer
from tabulate import tabulate

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
        resp = graph.get_relationships_by_path(
            input.relative_to(graph.repo_path),
            relationship,
            depth,
        )
    obj_id, sources, targets = resp["obj_id"], resp["sources"], resp["targets"]
    log_outputs(obj_id, relationship, sources, targets)


def log_outputs(
    obj_id: str,
    relationship: RelationshipType,
    sources: List[Dict[str, Any]],
    targets: List[Dict[str, Any]],
) -> None:
    headers = ["ID", "Content Type", "Path", "Relationship Data"]
    if sources:
        tabular_sources = [
            [s["id"], s["content_type"], s["path"], s["rel_data"]] for s in sources
        ]
        logger.info(f"{relationship} relationships to {obj_id}:")
        logger.info(f"{tabulate(tabular_sources, headers, tablefmt='grid')}\n")
    else:
        logger.info(f"No {relationship} relationships to {obj_id}.\n")
    if targets:
        tabular_targets = [
            [t["id"], t["content_type"], t["path"], t["rel_data"]] for t in targets
        ]
        logger.info(f"{relationship} relationships from {obj_id}:")
        logger.info(f"{tabulate(tabular_targets, headers, tablefmt='grid')}\n")
    else:
        logger.info(f"No {relationship} relationships from {obj_id}.")
