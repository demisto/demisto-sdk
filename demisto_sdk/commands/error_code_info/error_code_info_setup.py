import sys

import typer

from demisto_sdk.commands.common.configuration import sdk
from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.error_code_info.error_code_info import print_error_info
from demisto_sdk.utils.utils import update_command_args_from_config_file


@logging_setup_decorator
def error_code(
    input: str = typer.Option(
        ..., "-i", "--input", help="The error code to search for."
    ),
):
    """
    Retrieves information about a specific error code.
    """
    update_command_args_from_config_file("error-code-info", {"input": input})
    sys.path.append(sdk.configuration.env_dir)

    if input:
        result = print_error_info(input)
    else:
        typer.echo("Provide an error code, e.g. `-i DO106`")
        result = 1

    sys.exit(result)
