import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
from demisto_sdk.commands.find_dependencies.find_dependencies import (
    remove_dependencies_from_id_set,
)
from demisto_sdk.utils.utils import update_command_args_from_config_file


@logging_setup_decorator
def create_id_set(
    ctx: typer.Context,
    input: str = typer.Option(
        "",
        "-i",
        "--input",
        help="Input file path, the default is the content repo.",
    ),
    output: str = typer.Option(
        "",
        "-o",
        "--output",
        help="Output file path, the default is the Tests directory.",
    ),
    fail_duplicates: bool = typer.Option(
        False,
        "-fd",
        "--fail-duplicates",
        help="Fails the process if any duplicates are found.",
    ),
    marketplace: str = typer.Option(
        "",
        "-mp",
        "--marketplace",
        help=(
            "The marketplace the id set are created for, that determines which packs "
            "are inserted to the id set, and which items are present in the id set for "
            "each pack. Default is all packs exists in the content repository."
        ),
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
    Create the content dependency tree by IDs.
    """
    kwargs = {
        "input": input,
        "output": output,
        "fail_duplicates": fail_duplicates,
        "marketplace": marketplace,
    }

    update_command_args_from_config_file("create-id-set", kwargs)

    id_set_creator = IDSetCreator(**kwargs)  # type: ignore[arg-type]
    id_set, excluded_items_by_pack, excluded_items_by_type = (
        id_set_creator.create_id_set()
    )

    if excluded_items_by_pack:
        remove_dependencies_from_id_set(
            id_set,
            excluded_items_by_pack,
            excluded_items_by_type,
            marketplace,
        )
        id_set_creator.save_id_set()
