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
from demisto_sdk.commands.common.tools import get_file
from demisto_sdk.commands.content_graph.commands.get_relationships import Direction
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
    pack: str = typer.Argument(
        ...,
        help="The ID of the pack to check dependencies for.",
    ),
    show_reasons: bool = typer.Option(
        False,
        "-sr",
        "--show-reasons",
        is_flag=True,
        help="This flag prints all of the relationships between the given content pack and its dependencies.",
    ),
    dependency: str = typer.Option(
        None,
        "-d",
        "--dependency",
        show_default=True,
        case_sensitive=False,
        help="A specific dependency pack ID to get the data for.",
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
        "-m",
        "--mandatory-only",
        is_flag=True,
        help="If true, returns only the mandatory dependencies.",
    ),
    all_level_dependencies: bool = typer.Option(
        False,
        "-ald",
        "--all-level-dependencies",
        is_flag=True,
        help="If true, will retrieve all level of dependencies.",
    ),
    include_tests: bool = typer.Option(
        False,
        "--include-test-dependencies",
        is_flag=True,
        help="If true, will include tests dependencies in result.",
    ),
    include_hidden: bool = typer.Option(
        False,
        "--include-hidden",
        is_flag=True,
        help="If true, will include hidden packs in result.",
    ),
    direction: Direction = typer.Option(
        Direction.TARGETS,
        "-dir",
        "--direction",
        show_default=True,
        case_sensitive=False,
        help="Specifies whether to return only dependents (sources), only dependencies (targets) or both.",
    ),
    no_update_graph: bool = typer.Option(
        False,
        "-nu",
        "--no-update-graph",
        is_flag=True,
        help="If provided, does not update the graph before querying. Default is to update the graph.",
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
    Returns pack's dependencies of a given content pack.
    """
    logging_setup(
        console_log_threshold=console_log_threshold,
        file_log_threshold=file_log_threshold,
        log_file_path=log_file_path,
    )
    with ContentGraphInterface() as graph:
        if not no_update_graph:
            update_content_graph(graph)
        result = get_dependencies_by_pack_path(
            graph,
            pack,
            show_reasons,
            dependency,
            all_level_dependencies,
            marketplace,
            direction,
            mandatory_only,
            include_tests,
            False,
            include_hidden,
        )
        if output:
            (output / COMMAND_OUTPUTS_FILENAME).write_text(
                json.dumps(result, indent=4),
            )


def get_dependencies_by_pack_path(
    graph: ContentGraphInterface,
    pack_id: str,
    show_reasons: bool,
    dependency_pack: str,
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

    source_dependents, target_dependencies = graph.get_relationships_by_path(
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

    if dependency_pack:
        source_dependents = [
            dependency_obj
            for dependency_obj in source_dependents
            if dependency_obj.get("object_id") == dependency_pack
        ]
        target_dependencies = [
            dependency_obj
            for dependency_obj in target_dependencies
            if dependency_obj.get("object_id") == dependency_pack
        ]

    if show_reasons:
        add_reasons_to_dependencies(
            pack_id,
            source_dependents,
            target_dependencies,
            get_file(graph.import_path / graph.DEPENDS_ON_FILE_NAME),  # type: ignore
            mandatory_only,
            include_tests,
        )

    logger.info("[cyan]====== SUMMARY ======[/cyan]")
    if retrieve_sources:
        logger.info(
            f"Sources Dependents:\n{to_tabulate(source_dependents, show_reasons)}\n"
        )
    if retrieve_targets:
        logger.info(
            f"Target Dependencies:\n{to_tabulate(target_dependencies, show_reasons)}\n"
        )
    return {
        "source_dependents": source_dependents,
        "target_dependencies": target_dependencies,
    }


def to_tabulate(
    data: list,
    show_reasons: bool,
) -> str:
    if not data:
        return "No results."

    headers = ["Pack", "Mandatory", "Depth"]
    fieldnames_to_collect = ["name", "mandatorily", "minDepth"]

    if show_reasons:
        headers.append("Reasons")
        fieldnames_to_collect.append("formatted_reasons")

    tabulated_data = []
    for record in data:
        if show_reasons:
            format_reasons(record)
        tabulated_data.append([record[f] for f in fieldnames_to_collect])

    return tabulate(
        tabulated_data,
        headers=headers,
        tablefmt="fancy_grid",
    )


def add_reasons_to_dependencies(
    pack_id: str,
    source_dependents: list,
    target_dependencies: list,
    depends_on_obj: dict,
    mandatory_only: bool,
    include_tests: bool,
):
    """
    Iterates over the resulted sources or/and targets dependencies and adds the dependency reasons.

    For first level dependencies, the reason will be the pack's content items USES relationships.
    For all level dependencies, the reason will be the DEPENDS_ON relationship path between the packs.

    Args:
        pack_id (str): The given pack ID.
        source_dependents (list): List of the dependent records.
        target_dependencies (list): List of the dependencies records.
        depends_on_obj (dict): The reasons data of the DEPENDS_ON relationships given from the depends_on.json file.
        mandatory_only (bool): Whether to return only mandatory dependencies.
        include_tests (bool): Whether to include test dependencies in the result.
    """

    def get_content_items_relationship_reasons(
        pack_depends_on_reasons: list, mandatory_only: bool, include_tests: bool
    ):
        reasons_result: Dict[str, list] = {}
        for reason in pack_depends_on_reasons:
            if (reason.get("mandatorily") or not mandatory_only) and (
                not reason.get("is_test") or include_tests
            ):
                reasons_result.setdefault(reason.get("source"), []).append(
                    reason.get("target")
                )
        return reasons_result

    def get_packs_relationship_reasons(
        record: dict, mandatory_only: bool, include_tests: bool
    ):
        reasons_result = []
        for path in record["paths"]:
            if (path.get("mandatorily") or not mandatory_only) and (
                not path.get("is_test") or include_tests
            ):
                reasons_result.append(
                    [
                        path_element["name"]
                        for idx, path_element in enumerate(path["path"])
                        if idx % 2 == 0
                    ]
                )
        return reasons_result

    def add_reasons_to_dependency(
        dependency_record: dict,
        pack_depends_on_obj: list,
        mandatory_only: bool,
        include_tests: bool,
    ):
        if dependency_record.get("minDepth") == 1:
            dependency_record["reasons"] = get_content_items_relationship_reasons(
                pack_depends_on_obj, mandatory_only, include_tests
            )
        else:
            dependency_record["reasons"] = get_packs_relationship_reasons(
                dependency_record, mandatory_only, include_tests
            )

    for dependency_record in source_dependents:
        pack_depends_on_obj = (
            depends_on_obj.get(dependency_record.get("object_id"), {}).get(pack_id)
            or []
        )
        add_reasons_to_dependency(
            dependency_record, pack_depends_on_obj, mandatory_only, include_tests
        )

    for dependency_record in target_dependencies:
        pack_depends_on_obj = (
            depends_on_obj.get(pack_id, {}).get(dependency_record.get("object_id"))
            or []
        )
        add_reasons_to_dependency(
            dependency_record, pack_depends_on_obj, mandatory_only, include_tests
        )


def format_reasons(dependency_record: dict):
    """
    Formats the dependency reasons to a readable MD output.

    Args:
        dependency_record (dict): A dependency record object.
    """

    def format_content_items_relationship_path(dependency_record: dict):
        reasons = ""
        for source, targets in dependency_record["reasons"].items():
            if len(targets) == 1:
                reasons += f"* {source} -> [USES] -> {targets[0]}\n"
            else:
                targets.sort()
                formatted_targets = "\n  - ".join(targets)  # type: ignore
                reasons += f"* {source} -> [USES]:\n  - {formatted_targets}\n"
        return reasons

    def format_packs_relationship_path(dependency_record):
        return "* " + "\n* ".join(
            [
                " -> [DEPENDS_ON] -> ".join([f"Pack:{pack}" for pack in path])
                for path in dependency_record["reasons"]
            ]
        )

    if dependency_record.get("minDepth") == 1:
        dependency_record["formatted_reasons"] = format_content_items_relationship_path(
            dependency_record
        )
    else:
        dependency_record["formatted_reasons"] = format_packs_relationship_path(
            dependency_record
        )
