from pathlib import Path

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.common.tools import parse_marketplace_kwargs
from demisto_sdk.utils.utils import update_command_args_from_config_file


@logging_setup_decorator
def init(
    ctx: typer.Context,
    name: str = typer.Option(
        None,
        "-n",
        "--name",
        help="The name of the directory and file you want to create",
    ),
    id: str = typer.Option(
        None, "--id", help="The id used in the yml file of the integration or script"
    ),
    output: Path = typer.Option(
        None, "-o", "--output", help="The output directory to write the object into."
    ),
    integration: bool = typer.Option(
        False,
        "--integration",
        help="Create an Integration based on BaseIntegration template",
    ),
    script: bool = typer.Option(
        False, "--script", help="Create a Script based on BaseScript example"
    ),
    xsiam: bool = typer.Option(
        False,
        "--xsiam",
        help="Create an Event Collector based on a template, with matching subdirectories",
    ),
    pack: bool = typer.Option(
        False, "--pack", help="Create a pack and its subdirectories"
    ),
    template: str = typer.Option(
        None,
        "-t",
        "--template",
        help="Create an Integration/Script based on a specific template",
    ),
    author_image: Path = typer.Option(
        None,
        "-a",
        "--author-image",
        help="Path to 'Author_image.png' (up to 4kb, 120x50)",
    ),
    demisto_mock: bool = typer.Option(
        False,
        "--demisto_mock",
        help="Copy the demistomock (for Script/Integration in a Pack)",
    ),
    common_server: bool = typer.Option(
        False,
        "--common-server",
        help="Copy CommonServerPython (for Script/Integration in a Pack)",
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
    Initialize a new Pack, Integration, or Script.
    If the script/integration flags are not present, a pack will be created with the given name.
    Otherwise, based on the flags provided, either a script or integration will be generated.
    """
    from demisto_sdk.commands.init.initiator import Initiator

    # Update args from configuration file
    update_command_args_from_config_file("init", ctx.params)
    marketplace = parse_marketplace_kwargs(ctx.params)

    # Initialize the initiator
    initiator = Initiator(marketplace=marketplace, **ctx.params)
    initiator.init()
