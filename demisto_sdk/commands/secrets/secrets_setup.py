import sys
from pathlib import Path
from typing import List

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.secrets.secrets import SecretsValidator
from demisto_sdk.utils.utils import update_command_args_from_config_file


@logging_setup_decorator
def secrets(
    ctx: typer.Context,
    input: str = typer.Option(
        None, "-i", "--input", help="Specify file to check secret on."
    ),
    post_commit: bool = typer.Option(
        False,
        "--post-commit",
        help="Whether the secrets check is done after you committed your files. "
        "Before you commit the files it should not be used. Mostly for build validations.",
    ),
    ignore_entropy: bool = typer.Option(
        False,
        "-ie",
        "--ignore-entropy",
        help="Ignore entropy algorithm that finds secret strings (passwords/api keys).",
    ),
    whitelist: str = typer.Option(
        "./Tests/secrets_white_list.json",
        "-wl",
        "--whitelist",
        help='Full path to whitelist file, file name should be "secrets_white_list.json"',
    ),
    prev_ver: str = typer.Option(
        None, "--prev-ver", help="The branch against which to run secrets validation."
    ),
    file_paths: List[Path] = typer.Argument(
        None,
        help="Paths to the files to check for secrets.",
        exists=True,
        resolve_path=True,
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
    Run the secrets validator to catch sensitive data before exposing your code to a public repository.

    You can attach the full path to manually allow an allow list.
    """
    if file_paths and not input:
        # If file_paths is given as an argument, use it as the input (if not provided via -i)
        input = ",".join([str(path) for path in file_paths])

    update_command_args_from_config_file("secrets", ctx.params)
    sdk = ctx.obj
    sys.path.append(sdk.configuration.env_dir)
    # Initialize the SecretsValidator
    secrets_validator = SecretsValidator(
        configuration=sdk.configuration,
        is_circle=post_commit,
        ignore_entropy=ignore_entropy,
        white_list_path=whitelist,
        input_path=input,
    )

    # Run the secrets validator and return the result
    result = secrets_validator.run()
    raise typer.Exit(result)
