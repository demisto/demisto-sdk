from pathlib import Path
from typing import Optional

import typer

from demisto_sdk.commands.common.constants import PACKS_DIR, MarketplaceVersions
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import (
    logging_setup,
)
from demisto_sdk.commands.content_graph.commands.get_relationships import (
    Direction,
    get_relationships_by_path,
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
        help="The pack to check dependencies for.",
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
        help="Whether or not to retrieve all level  or first level of dependencies only, default is all.",
    ),
    include_tests: bool = typer.Option(
        False,
        "--incude-test-dependencies",
        is_flag=True,
        help="If true, includes tests dependencies in outputs.",
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
        path: Path = Path(PACKS_DIR) / input
        depth: int = MAX_DEPTH if all_level_dependencies else 1
        if update_graph:
            update_content_graph(graph)
        result = get_relationships_by_path(
            graph,
            path,
            RelationshipType.DEPENDS_ON,
            ContentType.PACK,
            depth,
            marketplace,
            Direction.TARGETS,
            mandatory_only,
            include_tests,
        )
        if output:
            (output / COMMAND_OUTPUTS_FILENAME).write_text(
                json.dumps(result, indent=4),
            )
