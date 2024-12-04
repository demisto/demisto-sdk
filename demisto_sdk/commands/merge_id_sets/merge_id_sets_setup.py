import sys
from pathlib import Path

import typer

from demisto_sdk.commands.common.tools import logger


def merge_id_sets(
    ctx: typer.Context,
    id_set1: Path = typer.Option(
        ..., "-i1", "--id-set1", help="First id_set.json file path"
    ),
    id_set2: Path = typer.Option(
        ..., "-i2", "--id-set2", help="Second id_set.json file path"
    ),
    output: Path = typer.Option(
        ..., "-o", "--output", help="File path of the united id_set"
    ),
    fail_duplicates: bool = typer.Option(
        False,
        "-fd",
        "--fail-duplicates",
        help="Fails the process if any duplicates are found.",
    ),
    console_log_threshold: str = typer.Option(
        None,
        "--console-log-threshold",
        help="Minimum logging threshold for console output. Possible values: DEBUG, INFO, SUCCESS, WARNING, ERROR.",
    ),
    file_log_threshold: str = typer.Option(
        None, "--file-log-threshold", help="Minimum logging threshold for file output."
    ),
    log_file_path: str = typer.Option(
        None, "--log-file-path", help="Path to save log files."
    ),
):
    """
    Merge two id_sets.
    """
    from demisto_sdk.commands.common.update_id_set import merge_id_sets_from_files
    from demisto_sdk.utils.utils import update_command_args_from_config_file

    kwargs = {
        "id_set1": id_set1,
        "id_set2": id_set2,
        "output": output,
        "fail_duplicates": fail_duplicates,
    }

    update_command_args_from_config_file("merge-id-sets", kwargs)

    first = kwargs["id_set1"]
    second = kwargs["id_set2"]
    output = kwargs["output"]
    fail_duplicates = kwargs["fail_duplicates"]

    _, duplicates = merge_id_sets_from_files(
        first_id_set_path=str(first),
        second_id_set_path=str(second),
        output_id_set_path=str(output),
    )

    if duplicates:
        logger.info(
            f"<red>Failed to merge ID sets: {first} with {second}, "
            f"there are entities with ID: {duplicates} that exist in both ID sets"
        )
        if fail_duplicates:
            sys.exit(1)
