from pathlib import Path

import typer

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.postman_codegen.postman_codegen import (
    postman_to_autogen_configuration,
)
from demisto_sdk.commands.split.ymlsplitter import YmlSplitter


@logging_setup_decorator
def postman_codegen(
    ctx: typer.Context,
    input: Path = typer.Option(
        ..., "-i", "--input", help="The Postman collection 2.1 JSON file"
    ),
    output: Path = typer.Option(
        Path("."),
        "-o",
        "--output",
        help="The output directory to save the config file or the integration",
    ),
    name: str = typer.Option(None, "-n", "--name", help="The output integration name"),
    output_prefix: str = typer.Option(
        None,
        "-op",
        "--output-prefix",
        help="The global integration output prefix. By default it is the product name.",
    ),
    command_prefix: str = typer.Option(
        None,
        "-cp",
        "--command-prefix",
        help="The prefix for each command in the integration. By default is the product name in lower case",
    ),
    config_out: bool = typer.Option(
        False,
        help="Used for advanced integration customization. Generates a config JSON file instead of integration.",
    ),
    package: bool = typer.Option(
        False,
        "-p",
        "--package",
        help="Generated integration will be split to package format instead of a YML file.",
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
    Use the `demisto sdk postman-codegen` command to generate an XSOAR integration (yml file) from a Postman Collection v2.1. Note the generated integration is in the yml format. Use the `demisto-sdk split` [command](package-dir#split-a-yml-file-to-directory-structure) to split the integration into the recommended [Directory Structure](package-dir) for further development.

    You can generate the integration either as a two-step process or a single step.
    - **Single Step:** Use this method to generate directly an integration yml file.
    - **Two Steps:** Use this method for more configuration and customization of the generated integration and code.
        1. Generate an integration config file.
        2. Update the config file as needed. Then generate the integration from the config file using the `demisto-sdk generate-integration` command.

    """
    sdk = ctx.obj
    postman_config = postman_to_autogen_configuration(
        collection=json.load(open(input)),  # Open the file directly
        name=name,
        command_prefix=command_prefix,
        context_path_prefix=output_prefix,
    )

    if config_out:
        path = Path(output) / f"config-{postman_config.name}.json"
        path.write_text(json.dumps(postman_config.to_dict(), indent=4))
        typer.echo(f"Config file generated at:\n{str(path.absolute())}")
    else:
        # Generate integration YML
        yml_path = postman_config.generate_integration_package(output, is_unified=True)
        if package:
            yml_splitter = YmlSplitter(
                configuration=sdk.configuration,
                file_type=FileType.INTEGRATION,
                input=str(yml_path),
                output=str(output),
            )
            yml_splitter.extract_to_package_format()
            typer.echo(
                f"<green>Package generated at {str(Path(output).absolute())} successfully</green>"
            )
        else:
            typer.echo(
                f"<green>Integration generated at {str(yml_path.absolute())} successfully</green>"
            )
