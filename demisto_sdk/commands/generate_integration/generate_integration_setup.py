from pathlib import Path

import typer

from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.generate_integration.code_generator import (
    IntegrationGeneratorConfig,
)


@logging_setup_decorator
def generate_integration(
    ctx: typer.Context,
    input: Path = typer.Option(
        ...,
        "-i",
        "--input",
        help="Config JSON file path from postman-codegen or openapi-codegen",
    ),
    output: Path = typer.Option(
        Path("."), "-o", "--output", help="Directory to save the integration package"
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
    Use the generate-integration command to generate a Cortex XSIAM/Cortex XSOAR integration from an integration config JSON file.
    The JSON config file can be generated from a Postman collection via the postman-codegen command.
    """
    # Open and load the JSON config file
    with input.open("r") as file:
        config_dict = json.load(file)

    # Initialize the integration generator config
    config = IntegrationGeneratorConfig(**config_dict)

    # Generate the integration package
    config.generate_integration_package(output, True)
