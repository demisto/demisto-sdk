import sys

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.error_code_info.error_code_info import print_error_info
from demisto_sdk.utils.utils import update_command_args_from_config_file


@logging_setup_decorator
def error_code(
    ctx: typer.Context,
    input: str = typer.Option(
        ..., "-i", "--input", help="The error code to search for."
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
    Retrieves information about a specific error code.
    """
    update_command_args_from_config_file("error-code-info", {"input": input})
    sdk = ctx.obj
    sys.path.append(sdk.configuration.env_dir)

    if input:
        result = print_error_info(input)
    else:
        typer.echo("Provide an error code, e.g. `-i DO106`")
        result = 1

    raise typer.Exit(result)
