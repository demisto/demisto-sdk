import sys

import typer

from demisto_sdk.commands.error_code_info.error_code_info import print_error_info
from demisto_sdk.config import get_config
from demisto_sdk.utils.utils import update_command_args_from_config_file

error_code_app = typer.Typer()


@error_code_app.command(
    name="error-code", help="Quickly find relevant information regarding an error code."
)
def error_code(
    input: str = typer.Option(
        ..., "-i", "--input", help="The error code to search for."
    ),
):
    """
    Retrieves information about a specific error code.
    """
    config = get_config()
    update_command_args_from_config_file("error-code-info", {"input": input})
    sys.path.append(config.configuration.env_dir)

    if input:
        result = print_error_info(input)
    else:
        typer.echo("Provide an error code, e.g. `-i DO106`")
        result = 1

    sys.exit(result)


if __name__ == "__main__":
    error_code_app()
